"""Back-in-stock subscriptions (S17) — 'notify me' on a sold-out variant; the restock fan-out
lives in stock_alert_service (invoked by the admin stock adjustment on the 0→positive edge)."""

from arvel import abort
from arvel.http import Request
from arvel.support import current_user
from arvel.validation import ValidationException

from app.models.product_variant import ProductVariant
from app.models.stock_alert import StockAlert
from app.models.user import User
from app.schemas import MessageOut


def _current_user() -> User:
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


async def subscribe(request: Request) -> MessageOut:
    """Watch a SOLD-OUT variant (in-stock → 422; duplicates are an idempotent no-op)."""
    user = _current_user()
    variant = await ProductVariant.find_or_fail(int(request.path_param("id")))
    if variant.stock > 0:
        raise ValidationException(
            {"variant": ["This variant is in stock — add it to your cart."]}
        )
    existing = (
        await StockAlert.where("product_variant_id", variant.id)
        .where("user_id", user.id)
        .first()
    )
    if existing is None:
        await StockAlert.create(product_variant_id=variant.id, user_id=user.id)
    return MessageOut(message="We'll email you when it's back.")


async def unsubscribe(request: Request) -> MessageOut:
    user = _current_user()
    await (
        StockAlert.where("product_variant_id", int(request.path_param("id")))
        .where("user_id", user.id)
        .delete()
    )
    return MessageOut(message="Alert removed.")
