from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPToken, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_verified', 'failed_login_attempts', 'is_active']
    list_filter = ['role', 'is_verified', 'is_active', 'biometric_enrolled']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'is_verified', 'biometric_enrolled')}),
    )


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'delivery_method', 'created_at', 'expires_at', 'is_used', 'attempts']
    list_filter = ['delivery_method', 'is_used', 'created_at']
    readonly_fields = ['token_hash', 'created_at', 'expires_at']
    search_fields = ['user__username', 'user__email']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['user__username', 'ip_address']
