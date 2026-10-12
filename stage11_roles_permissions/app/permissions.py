"""最小 RBAC：把角色映射为一组权限。"""

from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class Permission(str, Enum):
    ITEMS_READ = "items:read"
    USERS_READ = "users:read"


ROLE_PERMISSIONS = {
    Role.USER: frozenset({Permission.ITEMS_READ}),
    Role.ADMIN: frozenset({Permission.ITEMS_READ, Permission.USERS_READ}),
}
