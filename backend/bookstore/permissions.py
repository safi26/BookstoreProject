from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_manager(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
            or user.groups.filter(name="Manager").exists()
        )
    )


class IsManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_manager(request.user)


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return is_manager(request.user)


class IsCartOwner(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.pk == view.kwargs.get("user_id")
        )