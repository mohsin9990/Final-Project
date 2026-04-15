"""
Events Utility Functions
"""
from django.core.mail import send_mail
from django.conf import settings


def send_booking_confirmation_email(booking):
    """Send booking confirmation email"""
    subject = f'StarEvents - Booking Confirmation: {booking.event.title}'
    message = f"""
    Dear {booking.client.get_full_name() or booking.client.username},
    
    Your booking has been confirmed!
    
    Booking Reference: {booking.booking_reference}
    Event: {booking.event.title}
    Date: {booking.event.start_date}
    Venue: {booking.event.venue}
    Number of Tickets: {booking.number_of_tickets}
    Total Amount: £{booking.total_amount}
    
    Thank you for choosing StarEvents!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.client.email],
        fail_silently=False
    )
