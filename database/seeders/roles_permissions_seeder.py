"""Seed the RBAC graph — permissions, roles, role→permission grants, and one back-office user per
role. super-admin holds no explicit grants (it bypasses via the Gate.before hook)."""

from arvel.auth import Role
from arvel.auth import Permission as PermissionModel
from arvel.database import Seeder

from app.enums import ROLE_PERMISSIONS, Permission, RoleName
from app.models.user import User

# email → role for the seeded back-office accounts (password: "secret-admin").
BACK_OFFICE = {
    "super-admin@example.com": RoleName.SUPER_ADMIN,
    "catalog@example.com": RoleName.CATALOG_MANAGER,
    "orders@example.com": RoleName.ORDER_MANAGER,
    "support@example.com": RoleName.SUPPORT,
}


class RolesPermissionsSeeder(Seeder):
    """Idempotent: safe to re-run (each permission/role/user is first-or-created)."""

    async def run(self) -> None:
        for permission in Permission:
            if await PermissionModel.where("name", permission.value).first() is None:
                await PermissionModel.create(name=permission.value, guard_name="web")

        for role_name in RoleName:
            role = await Role.where("name", role_name.value).first()
            if role is None:
                role = await Role.create(name=role_name.value, guard_name="web")
                grants = ROLE_PERMISSIONS.get(role_name, [])
                if grants:
                    await role.give_permission_to(*(p.value for p in grants))

        for email, role_name in BACK_OFFICE.items():
            if await User.where("email", email).first() is not None:
                continue
            user = await User.create(
                name=role_name.value.replace("-", " ").title(),
                email=email,
                password="secret-admin",
                role="admin",  # legacy column kept for back-compat; authz is via permissions now
            )
            await user.assign_role(role_name.value)
