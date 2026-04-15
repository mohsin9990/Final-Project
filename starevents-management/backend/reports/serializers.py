"""
Reports Serializers
"""
from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    """Report Serializer"""
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'format', 'title', 'file_path',
            'file_size', 'parameters', 'generated_by', 'generated_by_name',
            'generated_at', 'expires_at'
        ]
        read_only_fields = ['id', 'generated_by', 'generated_at', 'file_size']
