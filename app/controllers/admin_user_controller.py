"""Admin user directory — find any user, see who they are, manage their roles.

``users.view`` gates the directory (support + order-manager have it; catalog-manager does NOT);
role mutations stay on the existing ``roles.manage`` endpoints. Responses expose ONLY the defined
schema — never password hashes, tokens, or reset material."""

from arvel.http import Request
from app.controllers.account_controller import avatar_url
from app.models.address import Address
from app.models.order import Order
from app.models.user import User
from app.schemas import AdminUserDetailOut, AdminUserOut, AdminUserPage


async def _user_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        roles=sorted(r.name for r in await user.roles()),
        avatar_url=await avatar_url(user, "chip"),
    )


async def index(
    request: Request, q: str = "", per_page: int = 20, page: int = 1
) -> AdminUserPage:
    """Search + paginate the user directory (name/email substring); users.view via the
    route's Authorize."""
    query = User.order_by("id")
    if q:
        like = f"%{q}%"
        query = query.where("email", "like", like).or_where("name", "like", like)
    result = await query.paginate(per_page, page)
    return AdminUserPage(
        data=[await _user_out(u) for u in result.items()],
        current_page=result.current_page(),
        last_page=result.last_page(),
        per_page=result.per_page(),
        total=result.total(),
    )


async def show(request: Request, id: User) -> AdminUserDetailOut:
    """One user: profile basics, roles, and an order summary. users.view is enforced by the
    route's Authorize middleware (DR-0055), so a denied caller 403s uniformly whether or not the
    user id exists."""
    user = id
    orders = await Order.where("user_id", user.id).get()
    base = await _user_out(user)
    return AdminUserDetailOut(
        id=base.id,
        name=base.name,
        email=base.email,
        email_verified=base.email_verified,
        roles=base.roles,
        orders_count=len(orders),
        total_spent_cents=sum(o.total_cents for o in orders),
        addresses_count=len(await Address.where("user_id", user.id).get()),
        avatar_url=base.avatar_url,
    )
