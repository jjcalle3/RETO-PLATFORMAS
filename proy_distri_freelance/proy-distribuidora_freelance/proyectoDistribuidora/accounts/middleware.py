from django.shortcuts import render

from .models import TenantStatus


class TenantStatusMiddleware:
    EXEMPT_PATHS = ['/login/', '/logout/', '/admin-panel/', '/admin/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            dist = getattr(request.user, 'distributor', None)
            if dist and dist.status == TenantStatus.SUSPENDED:
                if not any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
                    return render(request, 'accounts/tenant_suspended.html', status=403)
        return self.get_response(request)
