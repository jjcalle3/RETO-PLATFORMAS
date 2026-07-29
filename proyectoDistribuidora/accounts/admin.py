from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Distributor, DistributorInvitation, User, PasswordResetToken, Notification


class DistribuidorAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

admin.site.register(Distributor, DistribuidorAdmin)


class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'role', 'distributor', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('email',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Rol y Distribuidor', {'fields': ('role', 'distributor')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Rol y Distribuidor', {'fields': ('role', 'distributor')}),
    )

admin.site.register(User, UserAdmin)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at')
    search_fields = ('user__email',)
    list_filter = ('expires_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'order', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('user__email', 'message')


@admin.register(DistributorInvitation)
class DistributorInvitationAdmin(admin.ModelAdmin):
    list_display = ('target_email', 'created_by', 'created_at', 'expires_at', 'used_at', 'revoked_at')
    search_fields = ('target_email', 'created_by__email')
    list_filter = ('used_at', 'revoked_at')
