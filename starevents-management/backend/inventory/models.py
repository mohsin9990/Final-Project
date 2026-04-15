"""
Inventory Models - Inventory Management & Reporting System
Module: Inventory Management & Reporting (Masum Rana)
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class InventoryItem(models.Model):
    """
    Inventory Item Model for tracking event resources and equipment
    """
    CATEGORY_CHOICES = [
        ('equipment', 'Equipment'),
        ('consumable', 'Consumable'),
        ('furniture', 'Furniture'),
        ('decor', 'Decor'),
        ('audio_visual', 'Audio Visual'),
        ('catering', 'Catering'),
        ('other', 'Other'),
    ]
    
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('set', 'Set'),
        ('box', 'Box'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
        ('meter', 'Meter'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True)  # Stock Keeping Unit
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='piece')
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_stock = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_items'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum threshold"""
        return self.current_stock <= self.minimum_stock
    
    @property
    def stock_value(self):
        """Calculate total stock value"""
        return self.current_stock * self.unit_price


class StockTransaction(models.Model):
    """
    Stock Transaction Log for audit trail
    """
    TRANSACTION_TYPE_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('damaged', 'Damaged'),
    ]
    
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    previous_stock = models.DecimalField(max_digits=10, decimal_places=2)
    new_stock = models.DecimalField(max_digits=10, decimal_places=2)
    reference_event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions')
    reference_booking = models.ForeignKey('events.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_transactions')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory_item', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
            models.Index(fields=['created_at']),  # For GDPR retention cleanup
        ]
    
    def __str__(self):
        return f"{self.transaction_type} - {self.inventory_item.name} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New transaction
            self.previous_stock = self.inventory_item.current_stock
            if self.transaction_type == 'in' or self.transaction_type == 'return':
                self.new_stock = self.previous_stock + self.quantity
            elif self.transaction_type == 'out' or self.transaction_type == 'damaged':
                self.new_stock = max(0, self.previous_stock - self.quantity)
            else:  # adjustment
                self.new_stock = self.quantity
            
            # Update inventory item stock
            self.inventory_item.current_stock = self.new_stock
            self.inventory_item.save()
        
        super().save(*args, **kwargs)


class LowStockAlert(models.Model):
    """
    Low Stock Alert Log
    """
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='alerts')
    alert_sent_at = models.DateTimeField(auto_now_add=True)
    stock_level = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'low_stock_alerts'
        ordering = ['-alert_sent_at']
    
    def __str__(self):
        return f"Low Stock Alert - {self.inventory_item.name}"
