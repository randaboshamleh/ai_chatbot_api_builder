from rest_framework.permissions import BasePermission


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.tenant)


class IsTenantAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.tenant and
            request.user.role in ['owner', 'admin']
        )