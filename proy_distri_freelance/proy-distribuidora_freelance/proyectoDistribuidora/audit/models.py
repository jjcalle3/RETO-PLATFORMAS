from django.db import models

from accounts.models import User
from .managers import AuditLogQuerySet


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=100)

    entity_type = models.CharField(max_length=100)

    entity_id = models.CharField(max_length=100)

    # DR-04: typed columns for order-status transitions; blank for non-transition events
    previous_status = models.CharField(max_length=20, blank=True)

    new_status = models.CharField(max_length=20, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    details = models.JSONField(default=dict)

    objects = AuditLogQuerySet.as_manager()

    def __str__(self):
        return f"{self.action} - {self.entity_type}"