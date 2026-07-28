"""Custom managers/querysets for the accounts app.

Business-query managers only — the auth-related UserManager stays in
accounts/models.py (it extends BaseUserManager). Model classes/enums are
imported lazily inside methods to avoid a circular import with
accounts/models.py, which imports these at class-definition time.
"""
from django.db.models import Count, QuerySet
from django.db.models.manager import Manager


class DistributorQuerySet(QuerySet):
    def with_user_counts(self):
        """Annotate each distributor with its user count, ordered for the
        operator dashboard's table."""
        return self.annotate(user_count=Count('users')).order_by('status', 'name')

    def status_counts(self):
        """{status_value: count} across every TenantStatus, computed in the DB
        (was a Python tally loop over the whole distributor list)."""
        from .models import TenantStatus
        totales = {s.value: 0 for s in TenantStatus}
        for row in self.values('status').annotate(total=Count('id')):
            if row['status'] in totales:
                totales[row['status']] = row['total']
        return totales


class DistributorManager(Manager.from_queryset(DistributorQuerySet)):
    def create_with_admin(self, *, name, email, admin_email, admin_password):
        """Create a Distributor and its first DISTRIBUTOR-role user together.

        Deliberately opens NO transaction of its own — callers wrap it in the
        atomic block that fits their concurrency needs (crear_distribuidor's
        plain atomic; registrar_distribuidor's select_for_update lock block).
        Returns (distributor, admin_user).
        """
        from .models import Role, User
        distribuidor = self.create(name=name, email=email)
        admin = User.objects.create_user(
            email=admin_email,
            password=admin_password,
            role=Role.DISTRIBUTOR,
            distributor=distribuidor,
        )
        return distribuidor, admin


class NotificationQuerySet(QuerySet):
    def unread(self):
        return self.filter(is_read=False)

    def read(self):
        return self.filter(is_read=True)

    def mark_all_read(self):
        return self.unread().update(is_read=True)
