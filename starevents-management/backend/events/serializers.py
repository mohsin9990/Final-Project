"""
Events Serializers
"""
from rest_framework import serializers
from .models import Event, Booking, Notification


class EventSerializer(serializers.ModelSerializer):
    """Event Serializer"""
    available_capacity = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    is_past = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'category', 'image', 'venue',
            'start_date', 'end_date', 'capacity', 'available_capacity',
            'price', 'status', 'created_by', 'created_by_name',
            'is_full', 'is_past', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class BookingSerializer(serializers.ModelSerializer):
    """Booking Serializer"""
    event_title = serializers.CharField(source='event.title', read_only=True)
    client_name = serializers.CharField(source='client.username', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'event', 'event_title', 'client', 'client_name',
            'number_of_tickets', 'total_amount', 'status',
            'special_requests', 'booking_reference', 'is_waitlisted',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at'
        ]
        read_only_fields = [
            'id', 'client', 'booking_reference', 'total_amount',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at'
        ]
    
    def validate(self, attrs):
        event = attrs.get('event')
        number_of_tickets = attrs.get('number_of_tickets', 1)
        
        if event and event.available_capacity < number_of_tickets:
            if event.available_capacity > 0:
                raise serializers.ValidationError(
                    f'Only {event.available_capacity} tickets available'
                )
            else:
                attrs['is_waitlisted'] = True
        
        return attrs
    
    def create(self, validated_data):
        event = validated_data['event']
        number_of_tickets = validated_data.get('number_of_tickets', 1)
        
        # Calculate total amount
        validated_data['total_amount'] = event.price * number_of_tickets
        validated_data['client'] = self.context['request'].user
        
        booking = super().create(validated_data)
        
        # Update event capacity
        if not booking.is_waitlisted:
            # Send confirmation notification
            Notification.objects.create(
                user=booking.client,
                notification_type='booking_confirmation',
                title='Booking Confirmed',
                message=f'Your booking for {event.title} has been confirmed.',
                related_event=event,
                related_booking=booking
            )
        
        return booking


class NotificationSerializer(serializers.ModelSerializer):
    """Notification Serializer"""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'is_read', 'related_event', 'related_booking', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
