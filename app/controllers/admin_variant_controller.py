"""Admin variant + stock management, nested under the admin product resource; guarded by the same
catalog permissions as product mutations (deny-as-not-found). Stock changes are an explicit
operation (set or delta, with a reason) so the audit trail shows why; adjustments run under
SELECT..FOR UPDATE so concurrent changes serialize deterministically.
"""

from arvel import DB, abort
from arvel.activitylog import activity
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException, Validator

from app.models.cart_item import CartItem
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas import (
    MessageOut,
    StockAdjustIn,
    VariantIn,
    VariantOut,
    VariantUpdateIn,
)


def _current_user() -> User:
    user: User | None = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


def _out(variant: ProductVariant) -> VariantOut:
    return VariantOut(
        id=variant.id,
        sku=variant.sku,
        name=variant.name,
        price_adjustment_cents=variant.price_adjustment_cents,
        stock=variant.stock,
    )


async def _authorize(user: User, product: Product) -> None:
    """Variants are part of the product: mutating them needs update rights on the product
    (404 to non-admins so existence isn't leaked). ``product`` is already route-bound — on the
    update/stock/destroy routes it's resolved via ``.scope_bindings()``, which is also what makes
    a variant id from a DIFFERENT product 404 before this check ever runs."""
    if not await user.can("update", product):
        abort(404, "Product not found")


async def _sku_taken(
    product_id: int, sku: str, *, ignore_id: int | None = None
) -> bool:
    query = ProductVariant.where("product_id", product_id).where("sku", sku)
    if ignore_id is not None:
        existing = await query.first()
        return existing is not None and existing.id != ignore_id
    return await query.first() is not None


async def index(request: Request, id: Product) -> list[VariantOut]:
    user = _current_user()
    await _authorize(user, id)
    variants = await ProductVariant.where("product_id", id.id).order_by("id").get()
    return [_out(v) for v in variants]


async def store(request: Request, id: Product, data: VariantIn) -> VariantOut:
    user = _current_user()
    product = id
    await _authorize(user, product)
    validator = Validator(
        {"sku": data.sku, "name": data.name},
        {"sku": "required|string", "name": "required|string"},
    )
    if validator.fails():
        raise ValidationException(validator.errors())
    if data.stock < 0:
        raise ValidationException({"stock": ["Stock can't be negative."]})
    if await _sku_taken(product.id, data.sku):
        raise ValidationException({"sku": ["This SKU already exists on the product."]})
    variant = await ProductVariant.create(
        product_id=product.id,
        sku=data.sku,
        name=data.name,
        price_adjustment_cents=data.price_adjustment_cents,
        stock=data.stock,
    )
    await (
        activity()
        .caused_by(user)
        .performed_on(variant)
        .with_properties({"sku": data.sku, "stock": data.stock})
        .log("created variant")
    )
    return _out(variant)


async def update(
    request: Request, id: Product, variant_id: ProductVariant, data: VariantUpdateIn
) -> VariantOut:
    user = _current_user()
    await _authorize(user, id)
    variant = variant_id
    if data.sku is not None:
        if await _sku_taken(variant.product_id, data.sku, ignore_id=variant.id):
            raise ValidationException(
                {"sku": ["This SKU already exists on the product."]}
            )
        variant.sku = data.sku
    if data.name is not None:
        variant.name = data.name
    if data.price_adjustment_cents is not None:
        variant.price_adjustment_cents = data.price_adjustment_cents
    await variant.save()
    await (
        activity()
        .caused_by(user)
        .performed_on(variant)
        .with_properties(
            {
                "changed": [
                    k
                    for k in ("sku", "name", "price_adjustment_cents")
                    if getattr(data, k) is not None
                ]
            }
        )
        .log("updated variant")
    )
    return _out(variant)


async def adjust_stock(
    request: Request, id: Product, variant_id: ProductVariant, data: StockAdjustIn
) -> VariantOut:
    """Set or shift a variant's stock — an explicit, audited operation, serialized under a row
    lock so concurrent adjustments are deterministic."""
    user = _current_user()
    await _authorize(user, id)
    variant = variant_id
    if (data.set is None) == (data.delta is None):
        raise ValidationException(
            {"stock": ["Provide exactly one of 'set' or 'delta'."]}
        )
    async with DB.transaction():
        locked = (
            await ProductVariant.where("id", variant.id)
            .lock_for_update()
            .first_or_fail()
        )
        before = locked.stock
        target = data.set if data.set is not None else before + (data.delta or 0)
        if target < 0:
            raise ValidationException({"stock": ["Stock can't go negative."]})
        locked.stock = target
        await locked.save()
    await (
        activity()
        .caused_by(user)
        .performed_on(locked)
        .with_properties(
            {"from": before, "to": target, "reason": data.reason or "unspecified"}
        )
        .log("adjusted stock")
    )
    # a genuine 0→positive edge wakes the back-in-stock subscribers (queued fan-out, one-shot)
    from app.services.stock_alert_service import notify_back_in_stock

    await notify_back_in_stock(locked, before=before, after=target)
    # K9 — the product page's live stock subscription
    from app.events.stock_changed import broadcast_stock

    await broadcast_stock(locked)
    return _out(locked)


async def destroy(
    request: Request, id: Product, variant_id: ProductVariant
) -> MessageOut:
    """Delete a variant. Order history can never dangle (422 when order lines reference it);
    cart lines holding it are removed — the cart re-renders without the dead line."""
    user = _current_user()
    await _authorize(user, id)
    variant = variant_id
    if await OrderItem.where("product_variant_id", variant.id).first() is not None:
        raise ValidationException(
            {
                "variant": [
                    "This variant has been ordered — archive the product instead."
                ]
            }
        )
    await CartItem.where("product_variant_id", variant.id).delete()
    await (
        activity()
        .caused_by(user)
        .performed_on(variant)
        .with_properties({"sku": variant.sku})
        .log("deleted variant")
    )
    await variant.delete()
    return MessageOut(message="Variant deleted.")
