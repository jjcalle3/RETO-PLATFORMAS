"""Custom queryset for the audit app."""
from django.db.models import QuerySet


class AuditLogQuerySet(QuerySet):
    def for_distributor(self, distributor):
        """Tenant-scoped log entries with the acting user eager-loaded
        (NFR-02.5). Ordering/limit are left to the caller — the audit page
        orders by -timestamp, the tenant-detail page by -id."""
        return self.filter(user__distributor=distributor).select_related('user')
