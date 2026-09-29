from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user

        return (
            user.is_authenticated
            and (
                user.is_superuser
                or user.groups.filter(name="Manager").exists()
            )
        )