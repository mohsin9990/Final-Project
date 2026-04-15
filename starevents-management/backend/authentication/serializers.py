"""
Authentication Serializers
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, OTPToken, AuditLog
import jwt
from datetime import datetime, timedelta
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    """User Serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_verified', 'biometric_enrolled']
        read_only_fields = ['id', 'is_verified']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User Registration Serializer"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role', 'phone_number']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Phase 1: Password Login Serializer"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            if user.is_account_locked():
                raise serializers.ValidationError('Account is locked. Please try again later.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class OTPRequestSerializer(serializers.Serializer):
    """Phase 2: OTP Request Serializer"""
    delivery_method = serializers.ChoiceField(choices=['sms', 'email'])
    
    def validate(self, attrs):
        user = self.context['user']
        if not user.phone_number and attrs['delivery_method'] == 'sms':
            raise serializers.ValidationError('Phone number not registered')
        if not user.email and attrs['delivery_method'] == 'email':
            raise serializers.ValidationError('Email not registered')
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    """Phase 2: OTP Verification Serializer"""
    otp = serializers.CharField(max_length=6)
    
    def validate(self, attrs):
        user = self.context['user']
        otp_token = OTPToken.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp_token:
            raise serializers.ValidationError('No valid OTP found. Please request a new OTP.')
        
        is_valid, message = otp_token.verify(attrs['otp'])
        if not is_valid:
            raise serializers.ValidationError(message)
        
        attrs['otp_token'] = otp_token
        return attrs


class FacialRecognitionSerializer(serializers.Serializer):
    """Phase 3: Facial Recognition Serializer"""
    image_data = serializers.CharField()  # Base64 encoded image
    
    def validate(self, attrs):
        user = self.context['user']
        if not user.biometric_enrolled:
            raise serializers.ValidationError('Biometric not enrolled')
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    """Audit Log Serializer"""
    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'ip_address', 'user_agent', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']
