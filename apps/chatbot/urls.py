from django.urls import path
from . import views
from . import webhooks

urlpatterns = [
    path('chat/query/', views.ChatQueryView.as_view()),
    path('chat/voice/', views.VoiceQueryView.as_view()),
    path('chat/sessions/', views.ChatSessionListView.as_view()),
    path('chat/sessions/<uuid:pk>/', views.ChatSessionDetailView.as_view()),
    path('webhook/telegram/<uuid:tenant_id>/', webhooks.TelegramWebhookView.as_view()),
    path('webhook/whatsapp/<uuid:tenant_id>/', webhooks.WhatsAppWebhookView.as_view()),
]