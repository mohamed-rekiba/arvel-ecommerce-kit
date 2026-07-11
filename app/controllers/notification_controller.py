"""Customer notifications API — the database channel of arvel's notification system, surfaced to the
signed-in customer (list + mark-all-read). Bearer-guarded; a customer only ever sees their own rows
(Notifiable scopes by notifiable_type + id)."""

from typing import Any, cast
from app.auth.require import require_user as _customer

from arvel.http import Request

from app.controllers.serializers import iso as _iso
from app.schemas import MessageOut, NotificationOut


def _out(row: Any) -> NotificationOut:
    # the model's "json" cast returns the payload already decoded to a dict (arvel stores it in a
    # TEXT column and owns the json.loads); `or {}` guards a null column.
    data = cast("dict[str, Any]", row.data or {})
    return NotificationOut(
        id=str(row.id),
        type=str(row.type),
        message=str(data.get("message", "")),
        read=row.read_at is not None,
        created_at=_iso(row.created_at),
    )


async def index(request: Request) -> list[NotificationOut]:
    """The signed-in customer's notifications, newest first."""
    return [_out(row) for row in await _customer().notifications()]


async def mark_read(request: Request) -> MessageOut:
    """Mark all of the customer's notifications as read."""
    await _customer().mark_all_notifications_as_read()
    return MessageOut(message="All notifications marked as read.")
