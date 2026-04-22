# apps/chatbot/web_chat_urls.py
from django.urls import path
from .web_chat_views import WebChatInitView, WebChatMessageView, WebChatHistoryView

urlpatterns = [
    path('init/', WebChatInitView.as_view(), name='web-chat-init'),
    path('message/', WebChatMessageView.as_view(), name='web-chat-message'),
    path('history/<uuid:session_id>/', WebChatHistoryView.as_view(), name='web-chat-history'),
]
