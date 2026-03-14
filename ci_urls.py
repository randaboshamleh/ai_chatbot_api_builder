"""Minimal URL config for CI testing - avoids drf_yasg and heavy imports."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.authentication.urls')),
    path('api/v1/', include('apps.documents.urls')),
    path('api/v1/', include('apps.chatbot.urls')),
    path('api/v1/', include('apps.tenants.urls')),
    path('api/v1/', include('apps.analytics.urls')),
]
