from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Publication, Announcement
from .serializers import (
    PublicationSerializer, PublicationCreateSerializer,
    PublicationListSerializer,
    AnnouncementSerializer, AnnouncementCreateSerializer,
)
from .permissions import (
    IsOperator, IsSecretaryGeneral, IsIscooaExecOrOperator
)
from drf_spectacular.utils import extend_schema


# ─── PUBLICATION VIEWS ────────────────────────────────────────────────────────

@extend_schema(tags=['Publications'])
class CreatePublicationView(generics.CreateAPIView):
    """
    POST /api/v1/publications/create/
    Secretary General creates a new publication.
    """
    serializer_class   = PublicationCreateSerializer
    permission_classes = [IsSecretaryGeneral]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publication = serializer.save(created_by=request.user)
        return Response(
            {
                'detail':   'Publication created successfully.',
                'pub_ref':  publication.pub_ref,
                'pub_type': publication.pub_type,
                'subject':  publication.subject,
                'status':   publication.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Publications'])
class AllPublicationsView(generics.ListAPIView):
    """
    GET /api/v1/publications/
    Secretary General sees all publications.
    Filter by ?pub_type=email|sms|announcement
    Filter by ?status=draft|sent|scheduled|pending_approval
    """
    serializer_class   = PublicationListSerializer
    permission_classes = [IsSecretaryGeneral]

    def get_queryset(self):
        qs = Publication.objects.all()
        pub_type = self.request.query_params.get('pub_type')
        if pub_type:
            qs = qs.filter(pub_type=pub_type)
        pub_status = self.request.query_params.get('status')
        if pub_status:
            qs = qs.filter(status=pub_status)
        return qs


@extend_schema(tags=['Publications'])
class PublicationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/publications/<id>/
    PUT  /api/v1/publications/<id>/
    Secretary General views or updates a publication.
    """
    permission_classes = [IsSecretaryGeneral]
    queryset           = Publication.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PublicationCreateSerializer
        return PublicationSerializer


@extend_schema(tags=['Publications'])
class SendPublicationView(APIView):
    """
    POST /api/v1/publications/<id>/send/
    Secretary General sends a publication immediately.
    In production this calls Postmark or Termii.
    For now we simulate a successful send.
    """
    permission_classes = [IsSecretaryGeneral]

    def post(self, request, pk):
        try:
            publication = Publication.objects.get(pk=pk)
        except Publication.DoesNotExist:
            return Response(
                {'detail': 'Publication not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if publication.status == Publication.Status.SENT:
            return Response(
                {'detail': 'This publication has already been sent.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Count recipients based on target group
        from accounts.models import User
        if publication.target_group == 'all_operators':
            recipient_count = User.objects.filter(role='op', is_active=True).count()
        elif publication.target_group == 'exco_members':
            recipient_count = User.objects.filter(role='is', is_active=True).count()
        elif publication.target_group == 'bot_members':
            recipient_count = User.objects.filter(role='bot', is_active=True).count()
        elif publication.target_group == 'all':
            recipient_count = User.objects.filter(is_active=True).count()
        else:
            recipient_count = User.objects.filter(role='op', is_active=True).count()

        # In production: call Postmark for email or Termii for SMS here
        publication.status          = Publication.Status.SENT
        publication.sent_at         = timezone.now()
        publication.recipient_count = recipient_count
        publication.save()

        # Send in-app notifications to all operators
        from accounts.models import User as UserModel
        from notifications.utils import send_bulk_notification
        operators = UserModel.objects.filter(role='op', is_active=True)
        send_bulk_notification(
            users      = operators,
            category   = 'general',
            title      = publication.subject,
            message    = publication.content[:200],
            related_id = str(publication.id),
        )

        return Response({
            'detail':           'Publication sent successfully.',
            'pub_ref':          publication.pub_ref,
            'recipient_count':  publication.recipient_count,
            'sent_at':          publication.sent_at,
        })


# ─── ANNOUNCEMENT VIEWS ───────────────────────────────────────────────────────

@extend_schema(tags=['Publications'])
class CreateAnnouncementView(generics.CreateAPIView):
    """
    POST /api/v1/publications/announcements/create/
    Secretary General creates a new announcement.
    Urgent announcements auto-set email and SMS to True.
    """
    serializer_class   = AnnouncementCreateSerializer
    permission_classes = [IsSecretaryGeneral]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save(
            created_by   = request.user,
            status       = Announcement.Status.PUBLISHED,
            publish_date = timezone.now(),
        )
        return Response(
            {
                'detail':     'Announcement created and published.',
                'ann_ref':    announcement.ann_ref,
                'title':      announcement.title,
                'priority':   announcement.priority,
                'send_email': announcement.send_email,
                'send_sms':   announcement.send_sms,
                'status':     announcement.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Publications'])
class AllAnnouncementsView(generics.ListAPIView):
    """
    GET /api/v1/publications/announcements/
    All authenticated users can view published announcements.
    Secretary General can also see drafts.
    Filter by ?priority=normal|high|urgent
    Filter by ?category=general_notice|emergency|meeting|compliance|agm
    """
    serializer_class   = AnnouncementSerializer
    permission_classes = [IsIscooaExecOrOperator]

    def get_queryset(self):
        qs = Announcement.objects.all()

        # Operators only see published announcements
        if self.request.user.role == 'op':
            qs = qs.filter(status=Announcement.Status.PUBLISHED)

        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        return qs


@extend_schema(tags=['Publications'])
class AnnouncementDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/publications/announcements/<id>/
    View a single announcement.
    """
    serializer_class   = AnnouncementSerializer
    permission_classes = [IsIscooaExecOrOperator]
    queryset           = Announcement.objects.all()


@extend_schema(tags=['Publications'])
class PublicationStatsView(APIView):
    """
    GET /api/v1/publications/stats/
    Secretary General sees publication statistics.
    """
    permission_classes = [IsSecretaryGeneral]

    def get(self, request):
        from django.db.models import Count, Sum

        publications = Publication.objects.all()
        announcements = Announcement.objects.all()

        pub_totals = publications.aggregate(
            total_recipients = Sum('recipient_count'),
            total_count      = Count('id'),
        )

        return Response({
            'publications': {
                'total':                pub_totals['total_count'] or 0,
                'total_recipients':     pub_totals['total_recipients'] or 0,
                'by_type': {
                    item['pub_type']: item['count']
                    for item in publications.values('pub_type').annotate(count=Count('id'))
                },
                'by_status': {
                    item['status']: item['count']
                    for item in publications.values('status').annotate(count=Count('id'))
                },
            },
            'announcements': {
                'total':      announcements.count(),
                'published':  announcements.filter(status='published').count(),
                'by_priority': {
                    item['priority']: item['count']
                    for item in announcements.values('priority').annotate(count=Count('id'))
                },
            },
        })