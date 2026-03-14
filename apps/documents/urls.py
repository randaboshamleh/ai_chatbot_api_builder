from django.urls import path
from . import views

urlpatterns = [
    path('documents/upload/', views.DocumentUploadView.as_view()),
    path('documents/', views.DocumentListView.as_view()),
    path('documents/<uuid:pk>/', views.DocumentDeleteView.as_view()),
    path('documents/<uuid:pk>/status/', views.DocumentStatusView.as_view()),
]