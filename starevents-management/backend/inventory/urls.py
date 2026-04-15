"""
Inventory URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet, StockTransactionViewSet, LowStockAlertViewSet

router = DefaultRouter()
router.register(r'items', InventoryItemViewSet, basename='inventory-item')
router.register(r'transactions', StockTransactionViewSet, basename='stock-transaction')
router.register(r'alerts', LowStockAlertViewSet, basename='low-stock-alert')

urlpatterns = [
    path('', include(router.urls)),
]
