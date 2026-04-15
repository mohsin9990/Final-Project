"""
Inventory Utility Functions
"""
from django.core.mail import send_mail
from django.conf import settings
from .models import LowStockAlert


def check_low_stock(item):
    """Check if item is low stock and create alert if needed"""
    if item.is_low_stock:
        # Check if there's already an unresolved alert
        existing_alert = LowStockAlert.objects.filter(
            inventory_item=item,
            is_resolved=False
        ).first()
        
        if not existing_alert:
            # Create new alert
            alert = LowStockAlert.objects.create(
                inventory_item=item,
                stock_level=item.current_stock,
                minimum_threshold=item.minimum_stock
            )
            send_low_stock_alert(alert)
            return alert
    return None


def send_low_stock_alert(alert):
    """Send low stock alert email to admins"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    admins = User.objects.filter(role='admin', is_active=True)
    subject = f'StarEvents - Low Stock Alert: {alert.inventory_item.name}'
    message = f"""
    Low Stock Alert!
    
    Item: {alert.inventory_item.name}
    SKU: {alert.inventory_item.sku}
    Current Stock: {alert.stock_level} {alert.inventory_item.unit}
    Minimum Threshold: {alert.minimum_threshold} {alert.inventory_item.unit}
    
    Please restock this item soon.
    """
    
    admin_emails = [admin.email for admin in admins if admin.email]
    if admin_emails:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False
        )
