# apps/analytics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('analytics/dashboard/', views.AnalyticsDashboardView.as_view()),
    path('analytics/queries/', views.AnalyticsQueriesView.as_view()),
]