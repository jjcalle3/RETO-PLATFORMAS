from rest_framework.permissions import BasePermission


class IsDistributor(BasePermission):
    """Restrict DRF access to authenticated DISTRIBUTOR-role users."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'DISTRIBUTOR'
        )
