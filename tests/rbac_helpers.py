"""Test helper — seed the RBAC graph (permissions, roles, grants) into a test connection, mirroring
RolesPermissionsSeeder but without users. Fixtures then assign a role to their seeded admin user."""

from typing import Any

from arvel.auth import Permission as PermissionModel
from arvel.auth import Role

from app.enums import ROLE_PERMISSIONS, Permission, RoleName


async def seed_rbac(db: Any) -> None:
    for model in (Role, PermissionModel):
        model.set_connection(db)
    for permission in Permission:
        await PermissionModel.create(name=permission.value, guard_name="web")
    for role_name in RoleName:
        role = await Role.create(name=role_name.value, guard_name="web")
        grants = ROLE_PERMISSIONS.get(role_name, [])
        if grants:
            await role.give_permission_to(*(p.value for p in grants))
