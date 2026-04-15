import os
import sys
import django

# Change to backend directory
os.chdir('backend')
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starevents.settings')
django.setup()

from authentication.models import User

try:
    user = User.objects.get(username='admin')
    user.set_password('password123')
    user.role = 'admin'
    user.is_staff = True
    user.is_superuser = True
    user.is_verified = True
    user.save()
    print('✅ Admin credentials configured:')
    print('   Username: admin')
    print('   Password: password123')
    print('   Role: Admin')
except User.DoesNotExist:
    user = User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='password123',
        role='admin'
    )
    user.is_verified = True
    user.save()
    print('✅ Admin user created:')
    print('   Username: admin')
    print('   Password: password123')
    print('   Role: Admin')
