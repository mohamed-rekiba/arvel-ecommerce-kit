"""The printable order invoice — server-rendered HTML via **arvel.views** (Jinja), the kit's
exercise of the views module. Owner-or-token guarded like every order read; strings are shaped
per the request locale here (the template stays logic-free)."""

from typing import Any

from arvel import view
from arvel.http import Request, Response

from app.controllers.cart_controller import line_presentation
from app.controllers.order_access import resolve_owned_order
from app.controllers.serializers import iso as _iso
from app.enums import OrderStatus, PaymentMethod
from app.i18n import active_locale

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "invoice": "Invoice",
        "status": "Status",
        "bill_to": "Bill / ship to",
        "payment": "Payment",
        "item": "Item",
        "qty": "Qty",
        "unit": "Unit price",
        "amount": "Amount",
        "subtotal": "Subtotal",
        "shipping": "Shipping",
        "tax": "Tax",
        "discount": "Discount",
        "total": "Total",
        "footer": "Thank you for shopping with ArvelShop — built on the arvel framework.",
        "gateway": "Paid online (gateway)",
        "cod": "Cash on delivery",
    },
    "fr": {
        "invoice": "Facture",
        "status": "Statut",
        "bill_to": "Facturation / livraison",
        "payment": "Paiement",
        "item": "Article",
        "qty": "Qté",
        "unit": "Prix unitaire",
        "amount": "Montant",
        "subtotal": "Sous-total",
        "shipping": "Livraison",
        "tax": "Taxes",
        "discount": "Réduction",
        "total": "Total",
        "footer": "Merci d'avoir choisi ArvelShop — construit sur le framework arvel.",
        "gateway": "Payé en ligne (passerelle)",
        "cod": "Paiement à la livraison",
    },
    "ar": {
        "invoice": "فاتورة",
        "status": "الحالة",
        "bill_to": "الفوترة / الشحن إلى",
        "payment": "الدفع",
        "item": "المنتج",
        "qty": "الكمية",
        "unit": "سعر الوحدة",
        "amount": "المبلغ",
        "subtotal": "المجموع الفرعي",
        "shipping": "الشحن",
        "tax": "الضريبة",
        "discount": "الخصم",
        "total": "الإجمالي",
        "footer": "شكرًا لتسوقك من ArvelShop — مبني على إطار عمل arvel.",
        "gateway": "مدفوع عبر الإنترنت",
        "cod": "الدفع عند الاستلام",
    },
}

_STATUS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "pending": "pending",
        "paid": "paid",
        "shipped": "shipped",
        "delivered": "delivered",
        "cancelled": "cancelled",
    },
    "fr": {
        "pending": "en attente",
        "paid": "payée",
        "shipped": "expédiée",
        "delivered": "livrée",
        "cancelled": "annulée",
    },
    "ar": {
        "pending": "قيد الانتظار",
        "paid": "مدفوع",
        "shipped": "تم الشحن",
        "delivered": "تم التسليم",
        "cancelled": "ملغى",
    },
}


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
    t = dict(_STRINGS[locale])
    status = (
        order.status
        if isinstance(order.status, OrderStatus)
        else OrderStatus(order.status)
    )
    raw_method = getattr(order, "payment_method", None) or PaymentMethod.GATEWAY
    method = (
        raw_method
        if isinstance(raw_method, PaymentMethod)
        else PaymentMethod(str(raw_method))
    )
    t["status_label"] = _STATUS_LABELS[locale][status.value]
    t["method_label"] = t[method.value]

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
