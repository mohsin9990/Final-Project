from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'format', 'generated_by', 'generated_at', 'file_size']
    list_filter = ['report_type', 'format', 'generated_at']
    search_fields = ['title', 'generated_by__username']
    readonly_fields = ['generated_at', 'file_size']
