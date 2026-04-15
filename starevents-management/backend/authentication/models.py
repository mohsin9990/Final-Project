"""
Authentication Models - 3-Phase Security System
Module: Security & Authentication (Shamail Tariq)
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
import hashlib


class User(AbstractUser):
    """
    Custom User Model with extended fields for authentication
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('client', 'Client'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    biometric_enrolled = models.BooleanField(default=False)
    biometric_embedding = models.BinaryField(null=True, blank=True)  # Encrypted facial data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def lock_account(self, duration_minutes=30):
        """Lock account after failed attempts"""
        self.account_locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save()
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save()
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False


class OTPToken(models.Model):
    """
    One-Time Password Token for 2FA
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_tokens')
    token = models.CharField(max_length=6)  # 6-digit OTP
    token_hash = models.CharField(max_length=64)  # Hashed token for security
    delivery_method = models.CharField(max_length=10, choices=[('sms', 'SMS'), ('email', 'Email')])
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    class Meta:
        db_table = 'otp_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_used', 'expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.username} - {self.delivery_method}"
    
    @classmethod
    def generate_otp(cls, user, delivery_method='email', expiry_minutes=10):
        """Generate a new OTP token"""
        # Generate 6-digit random OTP
        token = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        otp = cls.objects.create(
            user=user,
            token=token,  # Store plain for sending, but verify using hash
            token_hash=token_hash,
            delivery_method=delivery_method,
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        )
        return otp
    
    def verify(self, provided_token):
        """Verify OTP token"""
        if self.is_used:
            return False, "OTP already used"
        
        if timezone.now() > self.expires_at:
            return False, f"OTP expired at {self.expires_at}"
        
        if self.attempts >= self.max_attempts:
            return False, "Maximum attempts exceeded"
        
        # Verify token - check both plain (for debugging) and hash (for security)
        # In production, remove plain token check
        if provided_token == self.token:
            self.is_used = True
            self.attempts = 0
            self.save()
            return True, "OTP verified"
        
        # Also verify using hash
        provided_hash = hashlib.sha256(provided_token.encode()).hexdigest()
        if provided_hash == self.token_hash:
            self.is_used = True
            self.attempts = 0
            self.save()
            return True, "OTP verified"
        
        self.attempts += 1
        self.save()
        return False, f"Invalid OTP. Attempts remaining: {self.max_attempts - self.attempts}"
    
    def is_expired(self):
        """Check if OTP is expired"""
        return timezone.now() > self.expires_at


class AuditLog(models.Model):
    """
    Audit Log for security events and user actions
    """
    ACTION_CHOICES = [
        ('login_attempt', 'Login Attempt'),
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('biometric_used', 'Biometric Authentication Used'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.user} at {self.created_at}"
