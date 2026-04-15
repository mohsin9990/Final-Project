"""
Reports Models - Report Generation System
Module: Inventory Management & Reporting (Masum Rana)
"""
from django.db import models
from django.conf import settings


class Report(models.Model):
    """
    Report Model for tracking generated reports
    """
    REPORT_TYPE_CHOICES = [
        ('inventory_status', 'Inventory Status Report'),
        ('inventory_utilization', 'Inventory Utilization Report'),
        ('stock_summary', 'Stock Summary Report'),
        ('event_resources', 'Event Resources Report'),
        ('booking_summary', 'Booking Summary Report'),
        ('custom', 'Custom Report'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    title = models.CharField(max_length=200)
    file_path = models.CharField(max_length=500)  # Path to generated file
    file_size = models.IntegerField(null=True, blank=True)  # Size in bytes
    parameters = models.JSONField(default=dict, blank=True)  # Report parameters/filters
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # For GDPR data retention
    
    class Meta:
        db_table = 'reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['report_type', 'generated_at']),
            models.Index(fields=['generated_by', 'generated_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.format.upper()} ({self.generated_at})"
