"""Coupon domain rules — one place for validation + discount math, shared by the cart apply
endpoint (fast feedback) and checkout (authoritative re-validation under a row lock).

Every rejection is a distinct, field-keyed 422 so the storefront can say exactly why."""

from arvel.dates import Date
from arvel.validation import ValidationException

from app.enums import CouponType
from app.models.coupon import Coupon
from app.models.coupon_redemption import CouponRedemption


def _fail(reason: str) -> None:
    raise ValidationException({"coupon": [reason]})


def validate_window_and_state(coupon: Coupon | None, subtotal_cents: int) -> Coupon:
    """The stateless checks (existence, active, window, minimum). Returns the coupon."""
    if coupon is None:
        _fail("That code isn't valid.")
        raise AssertionError("unreachable")
    if not coupon.active:
        _fail("This code is no longer active.")
    now = Date.now()
    if coupon.starts_at is not None and now < coupon.starts_at:
        _fail("This code isn't active yet.")
    if coupon.ends_at is not None and now > coupon.ends_at:
        _fail("This code has expired.")
    if subtotal_cents < (coupon.min_subtotal_cents or 0):
        _fail("Your order doesn't reach this code's minimum.")
    if coupon.usage_limit is not None and coupon.uses >= coupon.usage_limit:
        _fail("This code has been fully redeemed.")
    return coupon


async def enforce_per_customer_limit(
    coupon: Coupon, *, user_id: int | None, contact_email: str
) -> None:
    """Checkout-time only (a guest has no identity until they type their email)."""
    if coupon.per_customer_limit is None:
        return
    query = CouponRedemption.where("coupon_id", coupon.id)
    if user_id is not None:
        query = query.where("user_id", user_id)
    else:
        query = query.where("contact_email", contact_email)
    used = len(await query.get())
    if used >= coupon.per_customer_limit:
        _fail("You've already used this code the maximum number of times.")


def discount_cents(coupon: Coupon, subtotal_cents: int) -> int:
    """The discount this coupon takes off ``subtotal_cents`` — never below zero overall."""
    kind = (
        coupon.type if isinstance(coupon.type, CouponType) else CouponType(coupon.type)
    )
    if kind is CouponType.PERCENT:
        return int(min(subtotal_cents * coupon.value // 100, subtotal_cents))
    return int(min(coupon.value, subtotal_cents))


def normalize_code(code: str) -> str:
    return code.strip().upper()
