"""The printable order invoice — server-rendered HTML via arvel.views (Jinja). Owner-or-token
guarded like every order read. User-facing strings come from the framework translator
(resources/lang/<locale>/shop.json, ``invoice`` group), so the controller holds no copy — the
template stays logic-free."""

from typing import Any

from arvel import view
from arvel.http import Request, Response

from app.controllers.cart_controller import line_presentation
from app.controllers.order_access import resolve_owned_order
from app.controllers.serializers import iso as _iso
from app.enums import OrderStatus, PaymentMethod
from app.i18n import active_locale, trans_in

# the flat invoice UI strings under shop.invoice.* (status labels + payment methods are nested)
_LABELS = (
    "invoice",
    "status_heading",  # shop.invoice.status is the nested value-label map, not the header word
    "bill_to",
    "payment",
    "item",
    "qty",
    "unit",
    "amount",
    "subtotal",
    "shipping",
    "tax",
    "discount",
    "total",
    "footer",
)


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


async def show(request: Request) -> Response:
    order = await resolve_owned_order(
        request,
        int(request.path_param("id")),
        query_token=str(request.query("token", "") or ""),
    )
    items = await order.items().get()
    locale = active_locale()
    t: dict[str, str] = {k: trans_in(locale, f"shop.invoice.{k}") for k in _LABELS}
    # status/payment_method are cast to their enums by Order.__casts__
    status: OrderStatus = order.status
    method: PaymentMethod = order.payment_method
    # the translator returns the key itself on a miss, so an unmapped status degrades to a readable
    # fallback instead of 500-ing the invoice
    t["status_label"] = trans_in(locale, f"shop.invoice.status.{status.value}")
    t["method_label"] = trans_in(locale, f"shop.invoice.{method.value}")

    looks = await line_presentation([i.product_variant_id for i in items])
    lines: list[dict[str, Any]] = [
        {
            "name": i.product_name,
            "variant": i.variant_name,
            "qty": i.quantity,
            "unit": _money(i.unit_price_cents),
            "total": _money(i.unit_price_cents * i.quantity),
            "image": looks.get(i.product_variant_id, ("", "", None))[2],
        }
        for i in items
    ]
    html = await view(
        "invoice",
        {
            "locale": locale,
            "t": t,
            "order": {
                "id": order.id,
                "placed_at": (_iso(getattr(order, "created_at", None)) or "")[:10],
                "ship_name": order.ship_name,
                "ship_line1": order.ship_line1,
                "ship_line2": order.ship_line2,
                "ship_city": order.ship_city,
                "ship_postal_code": order.ship_postal_code,
                "ship_country": order.ship_country,
                "contact_email": order.contact_email,
                "coupon_code": order.coupon_code,
            },
            "lines": lines,
            "money": {
                "subtotal": _money(order.subtotal_cents),
                "shipping": _money(order.shipping_cents),
                "tax": _money(order.tax_cents),
                "discount": _money(order.discount_cents)
                if order.discount_cents
                else None,
                "total": _money(order.total_cents),
            },
        },
    ).render()
    return Response(
        content=html,
        headers={
            "content-type": "text/html; charset=utf-8",
            # the receipt token rides the URL — never let it leak via a Referer header
            "referrer-policy": "no-referrer",
        },
    )
