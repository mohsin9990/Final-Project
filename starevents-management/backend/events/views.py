"""
Events API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import Event, Booking, Notification
from .serializers import EventSerializer, BookingSerializer, NotificationSerializer
from .utils import send_booking_confirmation_email


class EventViewSet(viewsets.ModelViewSet):
    """Event ViewSet"""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Event.objects.all()
        status_filter = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category:
            queryset = queryset.filter(category=category)
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an event"""
        event = self.get_object()
        if request.user.role != 'admin' and event.created_by != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        event.status = 'published'
        event.save()
        return Response({'message': 'Event published'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an event"""
        event = self.get_object()
        if request.user.role != 'admin' and event.created_by != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        event.status = 'cancelled'
        event.save()
        
        # Notify all booked users
        bookings = event.bookings.filter(status='confirmed')
        for booking in bookings:
            Notification.objects.create(
                user=booking.client,
                notification_type='event_cancellation',
                title='Event Cancelled',
                message=f'The event {event.title} has been cancelled.',
                related_event=event,
                related_booking=booking
            )
        
        return Response({'message': 'Event cancelled'}, status=status.HTTP_200_OK)


class BookingViewSet(viewsets.ModelViewSet):
    """Booking ViewSet"""
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Booking.objects.all()
        return Booking.objects.filter(client=user)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking"""
        booking = self.get_object()
        
        # Allow admin, staff, or the booking owner to confirm
        if request.user.role not in ['admin', 'staff'] and booking.client != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        booking.status = 'confirmed'
        booking.save()
        
        # Send confirmation email
        send_booking_confirmation_email(booking)
        
        return Response({'message': 'Booking confirmed'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        if booking.client != request.user and request.user.role not in ['admin', 'staff']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        booking.status = 'cancelled'
        booking.save()
        
        Notification.objects.create(
            user=booking.client,
            notification_type='booking_cancellation',
            title='Booking Cancelled',
            message=f'Your booking for {booking.event.title} has been cancelled.',
            related_event=booking.event,
            related_booking=booking
        )
        
        return Response({'message': 'Booking cancelled'}, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification ViewSet"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'}, status=status.HTTP_200_OK)
