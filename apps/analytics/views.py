# apps/analytics/views.py
from datetime import date, timedelta
from django.db.models import Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.documents.permissions import IsTenantMember
from apps.documents.models import Document
from apps.chatbot.models import ChatSession, ChatMessage
from .models import QueryLog


class AnalyticsDashboardView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant = request.user.tenant
        today = date.today()
        week_ago = today - timedelta(days=7)

        total_queries = ChatMessage.objects.filter(
            session__tenant=tenant, role='user'
        ).count()

        queries_today = ChatMessage.objects.filter(
            session__tenant=tenant,
            role='user',
            created_at__date=today,
        ).count()

        queries_this_week = ChatMessage.objects.filter(
            session__tenant=tenant,
            role='user',
            created_at__date__gte=week_ago,
        ).count()

        return Response({
            'documents': {
                'total': Document.objects.filter(tenant=tenant).count(),
                'indexed': Document.objects.filter(tenant=tenant, status='indexed').count(),
                'failed': Document.objects.filter(tenant=tenant, status='failed').count(),
                'pending': Document.objects.filter(tenant=tenant, status='pending').count(),
            },
            'queries': {
                'total': total_queries,
                'today': queries_today,
                'this_week': queries_this_week,
            },
            'sessions': {
                'total': ChatSession.objects.filter(tenant=tenant).count(),
            },
        })


class AnalyticsQueriesView(APIView):
    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant = request.user.tenant
        
        # Get query logs
        query_logs = QueryLog.objects.filter(tenant=tenant).order_by('-created_at')[:50]
        
        # Calculate stats
        total_queries = query_logs.count()
        avg_response_time = query_logs.aggregate(Avg('response_time'))['response_time__avg'] or 0
        success_rate = 100  # Placeholder - you can calculate based on your criteria
        
        # Format recent queries
        recent_queries = []
        for log in query_logs[:10]:
            recent_queries.append({
                'id': str(log.id),
                'query': log.query,
                'answer': log.answer[:100] + '...' if len(log.answer) > 100 else log.answer,
                'response_time': log.response_time,
                'created_at': log.created_at.isoformat(),
            })
        
        return Response({
            'total_queries': total_queries,
            'avg_response_time': avg_response_time,
            'success_rate': success_rate,
            'recent_queries': recent_queries,
        })