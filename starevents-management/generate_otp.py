import os
import sys
import django

# Change to backend directory
os.chdir('backend')
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starevents.settings')
django.setup()

from authentication.models import User, OTPToken
from django.utils import timezone

# Get admin user
user = User.objects.get(username='admin')

# Generate OTP for email
otp = OTPToken.generate_otp(user=user, delivery_method='email', expiry_minutes=10)

print('✅ OTP Generated for Admin User:')
print(f'   Username: admin')
print(f'   OTP Code: {otp.token}')
print(f'   Method: Email')
print(f'   Expires: {otp.expires_at.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'   Valid for: 10 minutes')
