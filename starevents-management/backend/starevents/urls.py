"""
URL configuration for StarEvents Management System
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_root(_request):
    return JsonResponse({
        'status': 'ok',
        'service': 'StarEvents Backend API',
        'endpoints': [
            '/admin/',
            '/api/auth/',
            '/api/events/',
            '/api/inventory/',
            '/api/reports/',
        ],
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/events/', include('events.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
