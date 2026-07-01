from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Resolution, ResolutionVote, AdvisoryNote
from .serializers import (
    ResolutionSerializer, ResolutionCreateSerializer,
    ResolutionListSerializer,
    CastResolutionVoteSerializer,
    SubmitAdvisoryNoteSerializer,
)
from .permissions import (
    IsBOTMember, IsAdvisor, IsBOTOrAdvisor, CanDraftResolution
)
from drf_spectacular.utils import extend_schema


# ─── RESOLUTION MANAGEMENT VIEWS ─────────────────────────────────────────────

@extend_schema(tags=['Resolutions'])
class CreateResolutionView(generics.CreateAPIView):
    """
    POST /api/v1/resolutions/create/
    President, Treasurer, Legal Adviser or BOT member
    creates a new resolution.
    """
    serializer_class   = ResolutionCreateSerializer
    permission_classes = [CanDraftResolution]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resolution = serializer.save(
            proposed_by   = request.user,
            proposed_date = timezone.now().date(),
            association   = request.user.association,
        )
        return Response(
            {
                'detail':   'Resolution created successfully.',
                'res_ref':  resolution.res_ref,
                'title':    resolution.title,
                'status':   resolution.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Resolutions'])
class AllResolutionsView(generics.ListAPIView):
    """
    GET /api/v1/resolutions/
    BOT members, Advisors, President can see all resolutions.
    Filter by ?status=draft|pending|passed|rejected|deferred
    """
    serializer_class   = ResolutionListSerializer
    permission_classes = [IsBOTOrAdvisor]

    def get_queryset(self):
        qs = Resolution.objects.filter(
            association = self.request.user.association
        )
        res_status = self.request.query_params.get('status')
        if res_status:
            qs = qs.filter(status=res_status)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=['Resolutions'])
class ResolutionDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/resolutions/<id>/
    PUT /api/v1/resolutions/<id>/
    View or update a resolution.
    Only draft resolutions can be updated.
    """
    permission_classes = [CanDraftResolution]
    def get_queryset(self):
        return Resolution.objects.filter(
            association = self.request.user.association
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ResolutionCreateSerializer
        return ResolutionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def update(self, request, *args, **kwargs):
        resolution = self.get_object()
        if resolution.status != Resolution.Status.DRAFT:
            return Response(
                {'detail': 'Only draft resolutions can be edited.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)


@extend_schema(tags=['Resolutions'])
class PublishResolutionView(APIView):
    """
    POST /api/v1/resolutions/<id>/publish/
    Moves a draft resolution to pending
    so BOT members can vote on it.
    """
    permission_classes = [CanDraftResolution]

    def post(self, request, pk):
        try:
            resolution = Resolution.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Resolution.DoesNotExist:
            return Response(
                {'detail': 'Resolution not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if resolution.status != Resolution.Status.DRAFT:
            return Response(
                {'detail': f'Only draft resolutions can be published for voting. This resolution is {resolution.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        resolution.status = Resolution.Status.PENDING
        resolution.save()

        return Response({
            'detail':  'Resolution published for BOT voting.',
            'res_ref': resolution.res_ref,
            'status':  resolution.status,
        })


# ─── BOT VOTING VIEWS ─────────────────────────────────────────────────────────

@extend_schema(tags=['Resolutions'])
class CastResolutionVoteView(APIView):
    """
    POST /api/v1/resolutions/<id>/vote/
    BOT member casts a vote on a pending resolution.
    One vote per BOT member per resolution.
    After all votes are cast the result is determined automatically.
    """
    permission_classes = [IsBOTMember]

    def post(self, request, pk):
        try:
            resolution = Resolution.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Resolution.DoesNotExist:
            return Response(
                {'detail': 'Resolution not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if resolution.status != Resolution.Status.PENDING:
            return Response(
                {'detail': f'Voting is only allowed on pending resolutions. This resolution is {resolution.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check BOT member has not already voted
        if ResolutionVote.objects.filter(
            resolution = resolution,
            bot_member = request.user
        ).exists():
            return Response(
                {'detail': 'You have already voted on this resolution.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CastResolutionVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        choice = serializer.validated_data['choice']
        note   = serializer.validated_data.get('note', '')

        with transaction.atomic():
            ResolutionVote.objects.create(
                resolution = resolution,
                bot_member = request.user,
                choice     = choice,
                note       = note,
            )

            # Update live tally
            if choice == ResolutionVote.Choice.YEA:
                resolution.yea_count += 1
            elif choice == ResolutionVote.Choice.NAY:
                resolution.nay_count += 1
            else:
                resolution.abstain_count += 1
            resolution.save()

        return Response({
            'detail':        'Vote cast successfully.',
            'res_ref':       resolution.res_ref,
            'your_vote':     choice,
            'yea_count':     resolution.yea_count,
            'nay_count':     resolution.nay_count,
            'abstain_count': resolution.abstain_count,
            'total_votes':   resolution.total_votes,
        })

@extend_schema(tags=['Resolutions'])
class FinalizeResolutionView(APIView):
    """
    POST /api/v1/resolutions/<id>/finalize/
    President or BOT Chairman finalizes a resolution
    after all votes are in.
    Determines passed or rejected based on simple majority.
    Records signatories.
    """
    permission_classes = [CanDraftResolution]

    def post(self, request, pk):
        try:
            resolution = Resolution.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Resolution.DoesNotExist:
            return Response(
                {'detail': 'Resolution not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if resolution.status != Resolution.Status.PENDING:
            return Response(
                {'detail': 'Only pending resolutions can be finalized.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if resolution.total_votes == 0:
            return Response(
                {'detail': 'No votes have been cast yet.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine result by simple majority
        if resolution.yea_count > resolution.nay_count:
            final_status = Resolution.Status.PASSED
        else:
            final_status = Resolution.Status.REJECTED

        # Collect signatories from those who voted Yea
        yea_votes = ResolutionVote.objects.filter(
            resolution = resolution,
            choice     = ResolutionVote.Choice.YEA
        ).select_related('bot_member')

        signatories = [
            vote.bot_member.full_name
            for vote in yea_votes
        ]

        resolution_note = request.data.get('resolution_note', '')

        with transaction.atomic():
            resolution.status          = final_status
            resolution.ratified_date   = timezone.now()
            resolution.signatories     = signatories
            resolution.resolution_note = resolution_note
            resolution.save()

        return Response({
            'detail':          f'Resolution {final_status}.',
            'res_ref':         resolution.res_ref,
            'status':          resolution.status,
            'yea_count':       resolution.yea_count,
            'nay_count':       resolution.nay_count,
            'abstain_count':   resolution.abstain_count,
            'signatories':     resolution.signatories,
            'ratified_date':   resolution.ratified_date,
        })


@extend_schema(tags=['Resolutions'])
class DeferResolutionView(APIView):
    """
    POST /api/v1/resolutions/<id>/defer/
    BOT Chairman defers a resolution to next meeting.
    """
    permission_classes = [IsBOTMember]

    def post(self, request, pk):
        try:
            resolution = Resolution.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Resolution.DoesNotExist:
            return Response(
                {'detail': 'Resolution not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if resolution.status != Resolution.Status.PENDING:
            return Response(
                {'detail': 'Only pending resolutions can be deferred.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = request.data.get('note', '')
        resolution.status          = Resolution.Status.DEFERRED
        resolution.resolution_note = note
        resolution.save()

        return Response({
            'detail':  'Resolution deferred to next meeting.',
            'res_ref': resolution.res_ref,
            'status':  resolution.status,
        })


# ─── ADVISOR VIEWS ────────────────────────────────────────────────────────────

@extend_schema(tags=['Resolutions'])
class SubmitAdvisoryNoteView(APIView):
    """
    POST /api/v1/resolutions/<id>/advisory-note/
    Advisor submits a note on a resolution.
    One note per advisor per resolution.
    Note is visible to BOT and President.
    """
    permission_classes = [IsAdvisor]

    def post(self, request, pk):
        try:
            resolution = Resolution.objects.get(
                pk          = pk,
                association = request.user.association,
            )
        except Resolution.DoesNotExist:
            return Response(
                {'detail': 'Resolution not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check advisor has not already submitted a note
        if AdvisoryNote.objects.filter(
            resolution = resolution,
            advisor    = request.user
        ).exists():
            return Response(
                {'detail': 'You have already submitted an advisory note on this resolution.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmitAdvisoryNoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        note = AdvisoryNote.objects.create(
            resolution = resolution,
            advisor    = request.user,
            note       = serializer.validated_data['note'],
        )

        return Response({
            'detail':   'Advisory note submitted successfully.',
            'res_ref':  resolution.res_ref,
            'note':     note.note,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Resolutions'])
class MyAdvisoryNotesView(generics.ListAPIView):
    """
    GET /api/v1/resolutions/my-advisory-notes/
    Advisor views all their submitted notes.
    """
    permission_classes = [IsAdvisor]

    def get_queryset(self):
        from .models import AdvisoryNote
        return AdvisoryNote.objects.filter(advisor=self.request.user)

    def get_serializer_class(self):
        from .serializers import AdvisoryNoteSerializer
        return AdvisoryNoteSerializer