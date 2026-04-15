"""
Authentication URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet

# Use router for ViewSet with @action decorators
router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]
