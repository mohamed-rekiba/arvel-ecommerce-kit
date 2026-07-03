"""The customer address book — CRUD over saved shipping addresses, with a single-default rule
(the first address becomes the default; setting another default clears the rest). Checkout can
reference an entry by id; ownership is enforced everywhere (a foreign id is a 404)."""

from arvel import abort
from arvel.http import Request
from arvel.support import current_user

from app.models.address import Address
from app.models.user import User
from app.schemas import SavedAddressIn, SavedAddressOut


def _customer() -> User:
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    return user


def _out(address: Address) -> SavedAddressOut:
    return SavedAddressOut(
        id=address.id,
        label=address.label,
        name=address.name,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        postal_code=address.postal_code,
        country=address.country,
        phone=address.phone,
        is_default=bool(address.is_default),
    )


async def _owned(user: User, address_id: int) -> Address:
    address = await Address.find(address_id)
    if address is None or address.user_id != user.id:
        abort(404, "Address not found")
    return address


async def _clear_default(user: User) -> None:
    await (
        Address.where("user_id", user.id)
        .where("is_default", True)
        .update({"is_default": False})
    )


async def index(request: Request) -> list[SavedAddressOut]:
    user = _customer()
    rows = (
        await Address.where("user_id", user.id)
        .order_by("is_default", "desc")
        .order_by("id")
        .get()
    )
    return [_out(a) for a in rows]


async def store(request: Request, data: SavedAddressIn) -> SavedAddressOut:
    user = _customer()
    existing = await Address.where("user_id", user.id).get()
    make_default = data.is_default or not existing  # the first address is the default
    if make_default:
        await _clear_default(user)
    address = await Address.create(
        user_id=user.id,
        label=data.label,
        name=data.name,
        line1=data.line1,
        line2=data.line2,
        city=data.city,
        postal_code=data.postal_code,
        country=data.country.value,
        phone=data.phone,
        is_default=make_default,
    )
    return _out(address)


async def update(request: Request, data: SavedAddressIn) -> SavedAddressOut:
    user = _customer()
    address = await _owned(user, int(request.path_param("id")))
    if data.is_default and not address.is_default:
        await _clear_default(user)
    address.label = data.label
    address.name = data.name
    address.line1 = data.line1
    address.line2 = data.line2
    address.city = data.city
    address.postal_code = data.postal_code
    address.country = data.country.value
    address.phone = data.phone
    address.is_default = data.is_default or bool(address.is_default)
    await address.save()
    return _out(address)


async def destroy(request: Request) -> dict[str, str]:
    user = _customer()
    address = await _owned(user, int(request.path_param("id")))
    was_default = bool(address.is_default)
    await address.delete()
    if was_default:
        # promote the oldest remaining entry so the book always has a default when non-empty
        remaining = await Address.where("user_id", user.id).order_by("id").first()
        if remaining is not None:
            remaining.is_default = True
            await remaining.save()
    return {"status": "deleted"}
