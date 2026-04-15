from django.contrib import admin
from .models import InventoryItem, StockTransaction, LowStockAlert


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'current_stock', 'minimum_stock', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['inventory_item', 'transaction_type', 'quantity', 'new_stock', 'performed_by', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['inventory_item__name', 'inventory_item__sku']
    readonly_fields = ['previous_stock', 'new_stock', 'created_at']


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ['inventory_item', 'stock_level', 'minimum_threshold', 'alert_sent_at', 'is_resolved']
    list_filter = ['is_resolved', 'alert_sent_at']
    readonly_fields = ['alert_sent_at']
