from django.urls import path
from . import views

urlpatterns = [
    path('tenant/profile/', views.TenantProfileView.as_view()),
    path('tenant/api-key/rotate/', views.RotateApiKeyView.as_view()),
    path('tenant/stats/', views.TenantStatsView.as_view()),
    path('tenant/channels/', views.ChannelListView.as_view()),
]