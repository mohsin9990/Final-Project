"""
Inventory Serializers
"""
from rest_framework import serializers
from .models import InventoryItem, StockTransaction, LowStockAlert


class InventoryItemSerializer(serializers.ModelSerializer):
    """Inventory Item Serializer"""
    is_low_stock = serializers.ReadOnlyField()
    stock_value = serializers.ReadOnlyField()
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'description', 'sku', 'category', 'unit',
            'current_stock', 'minimum_stock', 'maximum_stock',
            'unit_price', 'supplier', 'location', 'is_active',
            'is_low_stock', 'stock_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockTransactionSerializer(serializers.ModelSerializer):
    """Stock Transaction Serializer"""
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = [
            'id', 'inventory_item', 'inventory_item_name', 'transaction_type',
            'quantity', 'previous_stock', 'new_stock', 'reference_event',
            'reference_booking', 'performed_by', 'performed_by_name',
            'notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'previous_stock', 'new_stock', 'performed_by', 'created_at'
        ]


class LowStockAlertSerializer(serializers.ModelSerializer):
    """Low Stock Alert Serializer"""
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    
    class Meta:
        model = LowStockAlert
        fields = [
            'id', 'inventory_item', 'inventory_item_name',
            'alert_sent_at', 'stock_level', 'minimum_threshold',
            'is_resolved', 'resolved_at'
        ]
        read_only_fields = ['id', 'alert_sent_at']
