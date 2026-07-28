from django.contrib import admin
from .models import AuditLog

class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'previous_status', 'new_status', 'user', 'timestamp')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_id', 'user__email')

admin.site.register(AuditLog, AuditLogAdmin)
