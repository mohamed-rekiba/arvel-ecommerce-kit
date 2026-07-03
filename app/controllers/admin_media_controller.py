"""The back-office media library — every stored file across the portfolio's HasMedia models
(product galleries, banners, customer avatars) in one list, each row resolved to its owner.
Read-only: deletion stays with the owning resource (e.g. the product-gallery delete route)."""

from typing import cast

from arvel import abort
from arvel.media import Media
from arvel.support import current_user

from app.controllers.serializers import iso as _iso
from app.enums import Permission
from app.models.banner import Banner
from app.models.product import Product
from app.models.user import User
from app.schemas import MediaItemOut

# media.model_type stores the owning class name (arvel HasMedia)
_OWNER_TYPES = {"Product": "product", "Banner": "banner", "User": "user"}


async def _owner_labels(rows: list[Media]) -> dict[tuple[str, int], str]:
    """Batch-resolve owner display labels per model type — one query per type, not per row."""
    ids: dict[str, set[int]] = {}
    for m in rows:
        ids.setdefault(m.model_type, set()).add(m.model_id)
    labels: dict[tuple[str, int], str] = {}
    if ids.get("Product"):
        for p in await Product.in_locale().where_in("id", list(ids["Product"])).get():
            labels[("Product", p.id)] = p.translation.name
    if ids.get("Banner"):
        for b in await Banner.where_in("id", list(ids["Banner"])).get():
            raw: object = b.translations
            translations: dict[str, dict[str, str]] = (
                cast("dict[str, dict[str, str]]", raw) if isinstance(raw, dict) else {}
            )
            title: str = (translations.get("en") or {}).get("title") or f"Banner #{b.id}"
            labels[("Banner", b.id)] = title
    if ids.get("User"):
        for u in await User.where_in("id", list(ids["User"])).get():
            labels[("User", u.id)] = u.name
    return labels


def _thumb_conversion(model_type: str) -> str:
    return {"Product": "thumb", "Banner": "mobile", "User": "chip"}.get(model_type, "")


async def index() -> list[MediaItemOut]:
    user = current_user.get()
    if user is None or not await user.can(Permission.CATALOG_VIEW.value):
        abort(403, "You may not browse the media library.")
    rows = await Media.order_by("id", "desc").get()
    labels = await _owner_labels(rows)
    out: list[MediaItemOut] = []
    for m in rows:
        conversion = _thumb_conversion(m.model_type)
        out.append(
            MediaItemOut(
                id=m.id,
                owner_type=_OWNER_TYPES.get(m.model_type) or m.model_type.lower(),
                owner_id=m.model_id,
                owner_label=labels.get(
                    (m.model_type, m.model_id), f"{m.model_type} #{m.model_id}"
                ),
                collection=m.collection_name,
                file_name=m.file_name,
                mime_type=m.mime_type,
                size=m.size,
                url=f"/api/media/{m.id}",
                thumb_url=(
                    f"/api/media/{m.id}/{conversion}"
                    if conversion and m.has_generated_conversion(conversion)
                    else None
                ),
                created_at=_iso(getattr(m, "created_at", None)),
            )
        )
    return out
