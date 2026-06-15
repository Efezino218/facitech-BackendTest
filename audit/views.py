from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count

from .models import AuditLog
from .serializers import AuditLogSerializer
from .permissions import IsSuperAdmin, IsPresidentOrSuperAdmin
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Audit'])
class AuditLogListView(generics.ListAPIView):
    """
    GET /api/v1/audit/
    Super Admin views the full audit log.
    Filter by ?action=create|update|approve|pay etc
    Filter by ?table=kyc_applications|bills etc
    Filter by ?user_email=someone@email.com
    Filter by ?user_role=op|is|bot|adv|sa
    """
    serializer_class   = AuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = AuditLog.objects.all()

        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)

        table = self.request.query_params.get('table')
        if table:
            qs = qs.filter(table_name__icontains=table)

        user_email = self.request.query_params.get('user_email')
        if user_email:
            qs = qs.filter(user_email__icontains=user_email)

        user_role = self.request.query_params.get('user_role')
        if user_role:
            qs = qs.filter(user_role=user_role)

        return qs


@extend_schema(tags=['Audit'])
class AuditLogDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/audit/<id>/
    Super Admin views a single audit log entry.
    """
    serializer_class   = AuditLogSerializer
    permission_classes = [IsSuperAdmin]
    queryset           = AuditLog.objects.all()


@extend_schema(tags=['Audit'])
class AuditStatsView(APIView):
    """
    GET /api/v1/audit/stats/
    Super Admin sees audit statistics.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        total = AuditLog.objects.count()

        by_action = AuditLog.objects.values('action').annotate(
            count=Count('id')
        ).order_by('-count')

        by_role = AuditLog.objects.values('user_role').annotate(
            count=Count('id')
        ).order_by('-count')

        by_table = AuditLog.objects.values('table_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        return Response({
            'total_entries': total,
            'by_action': {
                item['action']: item['count']
                for item in by_action
            },
            'by_role': {
                item['user_role']: item['count']
                for item in by_role
            },
            'top_tables': {
                item['table_name']: item['count']
                for item in by_table
            },
        })

@extend_schema(tags=['Audit'])
class MyActivityView(generics.ListAPIView):
    """
    GET /api/v1/audit/my-activity/
    Any authenticated user sees their own audit trail.
    Useful for operators to see their own actions.
    """
    serializer_class   = AuditLogSerializer
    permission_classes = [IsPresidentOrSuperAdmin]

    def get_queryset(self):
        return AuditLog.objects.filter(
            user=self.request.user
        )