"""
ASGI config for StarEvents Management System
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starevents.settings')

application = get_asgi_application()
