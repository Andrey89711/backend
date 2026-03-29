from rest_framework.permissions import BasePermission

SUPERADMIN = 'superadmin'
ADMIN = 'admin'
DIRECTOR = 'director'
MANAGER = 'manager'
ACCOUNTANT = 'accountant'
STOREKEEPER = 'storekeeper'

ALL_ROLES = (ADMIN, DIRECTOR, MANAGER, ACCOUNTANT, STOREKEEPER)


class IsSuperAdmin(BasePermission):
    """Разрешает доступ только Django superuser (is_superuser=True)."""

    def has_permission(self, request, _view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


def HasAnyRole(*roles):
    """
    Фабрика permission-классов для ролевого доступа.
    Доступ разрешён, если роль пользователя входит в переданный список.

    Пример использования:
        permission_classes = [HasAnyRole(ADMIN, MANAGER)]
        # или в get_permissions:
        return [HasAnyRole(ADMIN, MANAGER)()]
    """
    class RolePermission(BasePermission):
        allowed_roles = roles

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            if request.user.is_superuser:
                return True
            profile = getattr(request.user, 'profile', None)
            if profile is None:
                return False
            if profile.role not in self.allowed_roles:
                print(
                    f"[permissions] {request.method} {request.path} | "
                    f"user='{request.user.username}' role='{profile.role}' | "
                    f"required={list(self.allowed_roles)} → DENIED"
                )
                return False
            return True

    RolePermission.__name__ = f"HasAnyRole[{', '.join(roles)}]"
    return RolePermission
