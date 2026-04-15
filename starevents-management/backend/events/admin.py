from django.contrib import admin
from .models import Event, Booking, Notification


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'start_date', 'capacity', 'status', 'created_by']
    list_filter = ['status', 'category', 'start_date']
    search_fields = ['title', 'description', 'venue']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'event', 'client', 'number_of_tickets', 'status', 'created_at']
    list_filter = ['status', 'is_waitlisted', 'created_at']
    search_fields = ['booking_reference', 'client__username', 'event__title']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
