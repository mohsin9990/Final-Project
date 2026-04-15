"""
Inventory API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, F
from django.db import models
from django.utils import timezone
from .models import InventoryItem, StockTransaction, LowStockAlert
from .serializers import (
    InventoryItemSerializer, StockTransactionSerializer, LowStockAlertSerializer
)
from .utils import check_low_stock, send_low_stock_alert


class InventoryItemViewSet(viewsets.ModelViewSet):
    """Inventory Item ViewSet"""
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = InventoryItem.objects.all()
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        low_stock = self.request.query_params.get('low_stock')
        
        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
            )
        if low_stock == 'true':
            queryset = queryset.filter(current_stock__lte=models.F('minimum_stock'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """Adjust stock level"""
        item = self.get_object()
        adjustment_type = request.data.get('type')  # 'in', 'out', 'adjustment'
        quantity = float(request.data.get('quantity', 0))
        notes = request.data.get('notes', '')
        
        if adjustment_type == 'in':
            transaction_type = 'in'
        elif adjustment_type == 'out':
            transaction_type = 'out'
            quantity = -abs(quantity)
        else:
            transaction_type = 'adjustment'
        
        transaction = StockTransaction.objects.create(
            inventory_item=item,
            transaction_type=transaction_type,
            quantity=abs(quantity),
            performed_by=request.user,
            notes=notes
        )
        
        # Check for low stock after transaction
        if item.is_low_stock:
            check_low_stock(item)
        
        return Response({
            'message': 'Stock adjusted successfully',
            'transaction': StockTransactionSerializer(transaction).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def low_stock_items(self, request):
        """Get all low stock items"""
        items = InventoryItem.objects.filter(
            current_stock__lte=models.F('minimum_stock'),
            is_active=True
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Stock Transaction ViewSet (Read-only for audit)"""
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StockTransaction.objects.all()
        item_id = self.request.query_params.get('item_id')
        transaction_type = self.request.query_params.get('type')
        
        if item_id:
            queryset = queryset.filter(inventory_item_id=item_id)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        return queryset.order_by('-created_at')


class LowStockAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Low Stock Alert ViewSet"""
    queryset = LowStockAlert.objects.all()
    serializer_class = LowStockAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LowStockAlert.objects.filter(is_resolved=False).order_by('-alert_sent_at')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve low stock alert"""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'message': 'Alert resolved'}, status=status.HTTP_200_OK)
