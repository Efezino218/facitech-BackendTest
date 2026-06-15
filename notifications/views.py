from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from .utils import send_notification
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Notifications'])
class MyNotificationsView(generics.ListAPIView):
    """
    GET /api/v1/notifications/
    Any authenticated user views their own notifications.
    Filter by ?is_read=true|false
    Filter by ?category=bills|adverts|disputes etc
    """
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == 'true')
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


@extend_schema(tags=['Notifications'])
class UnreadCountView(APIView):
    """
    GET /api/v1/notifications/unread-count/
    Returns the count of unread notifications.
    Used for the badge count in the UI.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user    = request.user,
            is_read = False
        ).count()
        return Response({'unread_count': count})


@extend_schema(tags=['Notifications'])
class MarkReadView(APIView):
    """
    POST /api/v1/notifications/<id>/mark-read/
    Mark a single notification as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk   = pk,
                user = request.user
            )
        except Notification.DoesNotExist:
            return Response(
                {'detail': 'Notification not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        return Response({'detail': 'Notification marked as read.'})


@extend_schema(tags=['Notifications'])
class MarkAllReadView(APIView):
    """
    POST /api/v1/notifications/mark-all-read/
    Mark all unread notifications as read at once.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            user    = request.user,
            is_read = False
        ).update(
            is_read = True,
            read_at = timezone.now()
        )
        return Response({
            'detail':  f'{updated} notifications marked as read.',
            'updated': updated,
        })


@extend_schema(tags=['Notifications'])
class MyPreferencesView(APIView):
    """
    GET  /api/v1/notifications/preferences/
    POST /api/v1/notifications/preferences/
    User views or updates their notification preferences.
    Auto-creates preference record if not yet created.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)

    def post(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            prefs,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'detail':      'Notification preferences updated.',
                'preferences': serializer.data,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(tags=['Notifications'])
class TestNotificationView(APIView):
    """
    POST /api/v1/notifications/test/
    Creates a test notification for the current user.
    Used during development to verify the notification system.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        send_notification(
            user       = request.user,
            category   = 'general',
            title      = 'Test Notification',
            message    = 'This is a test notification from the ISCOOA Facitech platform.',
            related_id = '',
        )
        return Response({
            'detail': 'Test notification created successfully.',
        })