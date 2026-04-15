"""
Authentication Utility Functions
"""
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from .models import AuditLog


def send_otp_email(user, otp):
    """Send OTP via email"""
    subject = 'StarEvents - Your OTP Code'
    message = f'Your OTP code is: {otp}\n\nThis code will expire in 10 minutes.'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


def send_otp_sms(user, otp):
    """Send OTP via SMS using Twilio"""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        return False
    
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f'Your StarEvents OTP code is: {otp}. Valid for 10 minutes.',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=user.phone_number
        )
        return True
    except Exception:
        return False


def log_audit_event(user, action, request, details=None):
    """Log audit event"""
    AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        details=details or {}
    )


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
