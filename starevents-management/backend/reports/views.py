"""
Reports API Views - PDF and Excel Report Generation
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
from django.conf import settings
import os
from .models import Report
from .serializers import ReportSerializer
from .generators import (
    generate_inventory_status_pdf, generate_inventory_status_excel,
    generate_stock_summary_pdf, generate_stock_summary_excel,
    generate_event_resources_pdf, generate_event_resources_excel
)


class ReportViewSet(viewsets.ModelViewSet):
    """Report ViewSet"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Report.objects.all()
        return Report.objects.filter(generated_by=user)
    
    @action(detail=False, methods=['post'])
    def generate_inventory_status(self, request):
        """Generate Inventory Status Report"""
        format_type = request.data.get('format', 'pdf')
        category = request.data.get('category')
        
        if format_type == 'pdf':
            file_path = generate_inventory_status_pdf(request.user, category)
        else:
            file_path = generate_inventory_status_excel(request.user, category)
        
        # Create report record
        report = Report.objects.create(
            report_type='inventory_status',
            format=format_type,
            title=f'Inventory Status Report - {category or "All"}',
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            parameters={'category': category} if category else {},
            generated_by=request.user
        )
        
        return Response({
            'message': 'Report generated successfully',
            'report': ReportSerializer(report).data,
            'download_url': f'/api/reports/{report.id}/download/'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def generate_stock_summary(self, request):
        """Generate Stock Summary Report"""
        format_type = request.data.get('format', 'pdf')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if format_type == 'pdf':
            file_path = generate_stock_summary_pdf(request.user, start_date, end_date)
        else:
            file_path = generate_stock_summary_excel(request.user, start_date, end_date)
        
        report = Report.objects.create(
            report_type='stock_summary',
            format=format_type,
            title='Stock Summary Report',
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            parameters={'start_date': start_date, 'end_date': end_date},
            generated_by=request.user
        )
        
        return Response({
            'message': 'Report generated successfully',
            'report': ReportSerializer(report).data,
            'download_url': f'/api/reports/{report.id}/download/'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def generate_event_resources(self, request):
        """Generate Event Resources Report"""
        format_type = request.data.get('format', 'pdf')
        event_id = request.data.get('event_id')
        
        if format_type == 'pdf':
            file_path = generate_event_resources_pdf(request.user, event_id)
        else:
            file_path = generate_event_resources_excel(request.user, event_id)
        
        report = Report.objects.create(
            report_type='event_resources',
            format=format_type,
            title=f'Event Resources Report - Event {event_id}',
            file_path=file_path,
            file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            parameters={'event_id': event_id},
            generated_by=request.user
        )
        
        return Response({
            'message': 'Report generated successfully',
            'report': ReportSerializer(report).data,
            'download_url': f'/api/reports/{report.id}/download/'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download generated report"""
        report = self.get_object()
        
        if not os.path.exists(report.file_path):
            return Response({'error': 'Report file not found'}, status=status.HTTP_404_NOT_FOUND)
        
        file_extension = 'pdf' if report.format == 'pdf' else 'xlsx'
        content_type = 'application/pdf' if report.format == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return FileResponse(
            open(report.file_path, 'rb'),
            content_type=content_type,
            filename=f'{report.title}.{file_extension}'
        )
