"""RBAC tables — roles, permissions, and the pivots arvel's HasRoles/Role use
(``model_has_roles`` / ``model_has_permissions`` / ``role_has_permissions``)."""

from arvel.database import Blueprint, Migration, Schema


class CreatePermissionTables(Migration):
    def up(self, schema: Schema) -> None:
        def roles(t: Blueprint) -> None:
            t.id()
            t.string("name").unique()
            t.string("guard_name").default(value="web")
            t.timestamps()

        def permissions(t: Blueprint) -> None:
            t.id()
            t.string("name").unique()
            t.string("guard_name").default(value="web")
            t.timestamps()

        def model_has_roles(t: Blueprint) -> None:
            t.integer("role_id").index()
            t.string("model_type")
            t.integer("model_id").index()

        def model_has_permissions(t: Blueprint) -> None:
            t.integer("permission_id").index()
            t.string("model_type")
            t.integer("model_id").index()

        def role_has_permissions(t: Blueprint) -> None:
            t.integer("role_id").index()
            t.integer("permission_id").index()

        schema.create("roles", roles)
        schema.create("permissions", permissions)
        schema.create("model_has_roles", model_has_roles)
        schema.create("model_has_permissions", model_has_permissions)
        schema.create("role_has_permissions", role_has_permissions)

    def down(self, schema: Schema) -> None:
        for table in (
            "role_has_permissions",
            "model_has_permissions",
            "model_has_roles",
            "permissions",
            "roles",
        ):
            schema.drop(table)
