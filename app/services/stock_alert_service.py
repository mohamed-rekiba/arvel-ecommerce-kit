"""The restock fan-out (S17): on a genuine 0→positive stock edge, every subscriber gets a QUEUED
back-in-stock notification (database + mail ride separate worker jobs) and the subscription is
consumed — one-shot, so a later adjustment can't re-notify."""

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.stock_alert import StockAlert
from app.models.user import User
from app.notifications.back_in_stock_notification import BackInStockNotification


async def notify_back_in_stock(
    variant: ProductVariant, *, before: int, after: int
) -> int:
    """Fan out iff stock crossed 0→positive. Returns how many subscribers were notified."""
    if before > 0 or after <= 0:
        return 0
    alerts = await StockAlert.where("product_variant_id", variant.id).get()
    if not alerts:
        return 0
    product = await Product.with_trashed().where("id", variant.product_id).first()
    if product is None:
        return 0
    translations = {t.locale: t.name for t in product.translations}
    product_name = translations.get("en") or product.slug
    notified = 0
    for alert in alerts:
        user = await User.find(alert.user_id)
        await (
            alert.delete()
        )  # one-shot: consumed regardless (a dead user won't re-queue forever)
        if user is None:
            continue  # a vanished subscriber never 500s the fan-out
        await user.notify(
            BackInStockNotification(product_name, product.slug, variant.name)
        )
        notified += 1
    return notified
