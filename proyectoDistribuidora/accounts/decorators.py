from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


def role_required(*roles):
    """Restrict a view to authenticated users whose `role` is in `roles`.

    Unauthenticated -> redirect to login (like @login_required).
    Authenticated but wrong role -> 403, never a redirect, so a role can't be
    inferred by watching where the user bounces to (FR-02.3).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                return HttpResponseForbidden('No tienes permiso para acceder a esta página.')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def superuser_required(view_func):
    """Restrict a view to platform operators (is_superuser flag OR SUPER_ADMIN role).

    Accepts both so that superusers created via createsuperuser before the
    SUPER_ADMIN role existed (whose role field is blank) still pass through
    without a data migration.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        # Late import avoids a circular dependency at module load time.
        from .models import Role
        is_operator = request.user.is_superuser or request.user.role == Role.SUPER_ADMIN
        if not is_operator:
            return HttpResponseForbidden('No tienes permiso para acceder a esta página.')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
