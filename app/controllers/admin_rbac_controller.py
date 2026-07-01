"""Admin RBAC + audit API — manage roles/permissions and read the activity log.

Role management (list roles + their permissions, list permissions, assign/revoke a role on a user) is
gated on ``roles.manage``; the audit log is gated on ``audit.view``. super-admin bypasses both via the
Gate.before hook. Every mutation here is itself recorded in the activity log.
"""

from typing import Any

from arvel import abort
from arvel.activitylog import Activity, activity
from arvel.auth import Permission as PermissionModel
from arvel.auth import Role
from arvel.http import Request
from arvel.support import current_user

from app.enums import Permission
from app.models.user import User
from app.schemas import ActivityOut, AssignRoleIn, PermissionOut, RoleOut, UserRolesOut


async def _require(permission: Permission) -> User:
    user = current_user.get()
    if user is None:
        abort(401, "Unauthenticated")
    if not await user.can(permission.value):
        abort(403, "Insufficient permissions.")
    return user


async def _role_out(role: Any) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        permissions=sorted(p.name for p in await role.permissions()),
    )


async def roles_index(request: Request) -> list[RoleOut]:
    """List every role with the permissions it grants."""
    await _require(Permission.ROLES_MANAGE)
    return [await _role_out(role) for role in await Role.all()]


async def permissions_index(request: Request) -> list[PermissionOut]:
    """List every permission in the system."""
    await _require(Permission.ROLES_MANAGE)
    return [PermissionOut(id=p.id, name=p.name) for p in await PermissionModel.all()]


async def user_roles(request: Request) -> UserRolesOut:
    """The roles currently assigned to a user."""
    await _require(Permission.ROLES_MANAGE)
    user = await User.find_or_fail(int(request.path_param("id")))
    return UserRolesOut(
        user_id=user.id, roles=sorted(r.name for r in await user.roles())
    )


async def assign_role(request: Request, data: AssignRoleIn) -> UserRolesOut:
    """Assign a role to a user (roles.manage), recording it in the audit log."""
    admin = await _require(Permission.ROLES_MANAGE)
    if await Role.where("name", data.role).first() is None:
        abort(422, f"Unknown role: {data.role}")
    user = await User.find_or_fail(int(request.path_param("id")))
    await user.assign_role(data.role)
    await (
        activity()
        .caused_by(admin)
        .performed_on(user)
        .with_properties({"role": data.role, "action": "assign"})
        .log(f"assigned role '{data.role}'")
    )
    return UserRolesOut(
        user_id=user.id, roles=sorted(r.name for r in await user.roles())
    )


async def revoke_role(request: Request) -> UserRolesOut:
    """Revoke a role from a user (roles.manage), recording it in the audit log."""
    admin = await _require(Permission.ROLES_MANAGE)
    user = await User.find_or_fail(int(request.path_param("id")))
    role = request.path_param("role")
    await user.remove_role(role)
    await (
        activity()
        .caused_by(admin)
        .performed_on(user)
        .with_properties({"role": role, "action": "revoke"})
        .log(f"revoked role '{role}'")
    )
    return UserRolesOut(
        user_id=user.id, roles=sorted(r.name for r in await user.roles())
    )


def _iso(value: Any) -> str | None:
    """A timestamp → ISO-8601 string, whether it's an arvel Date (``to_iso``) or a stdlib datetime."""
    if value is None:
        return None
    for attr in ("to_iso", "isoformat"):
        fn = getattr(value, attr, None)
        if callable(fn):
            return str(fn())
    return str(value)


def _activity_out(row: Activity) -> ActivityOut:
    return ActivityOut(
        id=row.id,
        description=row.description,
        event=row.event,
        causer_id=row.causer_id,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        properties=dict(row.properties or {}),
        created_at=_iso(row.created_at),
    )


async def audit_index(request: Request) -> list[ActivityOut]:
    """The most recent audit-log entries (audit.view)."""
    await _require(Permission.AUDIT_VIEW)
    rows = await Activity.order_by("id", "desc").limit(50).get()
    return [_activity_out(row) for row in rows]
