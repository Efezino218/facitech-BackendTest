from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Poll, Vote
from .serializers import (
    PollSerializer, PollCreateSerializer,
    PollListSerializer, CastVoteSerializer,
)
from .permissions import IsOperator, IsIscooaExec, IsOperatorOrExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR POLL VIEWS ──────────────────────────────────────────────────────

@extend_schema(tags=['Polls'])
class ActivePollsView(generics.ListAPIView):
    """
    GET /api/v1/polls/active/
    Operator sees all active polls they can vote on.
    """
    serializer_class   = PollListSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Poll.objects.filter(status=Poll.Status.ACTIVE)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=['Polls'])
class PollDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/polls/<id>/
    Operator views a single poll with live tallies.
    """
    serializer_class   = PollSerializer
    permission_classes = [IsOperatorOrExec]
    queryset           = Poll.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=['Polls'])
class CastVoteView(APIView):
    """
    POST /api/v1/polls/<id>/vote/
    Operator casts a vote on an active poll.
    One vote per operator per poll enforced.
    """
    permission_classes = [IsOperator]

    def post(self, request, pk):
        try:
            poll = Poll.objects.get(pk=pk)
        except Poll.DoesNotExist:
            return Response(
                {'detail': 'Poll not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check poll is active
        if poll.status != Poll.Status.ACTIVE:
            return Response(
                {'detail': f'This poll is {poll.status}. Voting is not allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check poll has not closed
        if poll.closes_at and timezone.now() > poll.closes_at:
            return Response(
                {'detail': 'This poll has already closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check operator has not already voted
        if Vote.objects.filter(poll=poll, operator=request.user).exists():
            return Response(
                {'detail': 'You have already voted on this poll.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CastVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        choice = serializer.validated_data['choice']

        with transaction.atomic():
            Vote.objects.create(
                poll     = poll,
                operator = request.user,
                choice   = choice,
            )
            # Update live tally on the poll
            if choice == Vote.Choice.YES:
                poll.yes_count += 1
            else:
                poll.no_count += 1
            poll.save()

        return Response({
            'detail':       f'Vote cast successfully.',
            'poll_ref':     poll.poll_ref,
            'your_vote':    choice,
            'yes_count':    poll.yes_count,
            'no_count':     poll.no_count,
            'total_votes':  poll.total_votes,
            'yes_percentage': poll.yes_percentage,
            'no_percentage':  poll.no_percentage,
        })


# ─── ISCOOA EXECUTIVE POLL VIEWS ──────────────────────────────────────────────

@extend_schema(tags=['Polls'])
class CreatePollView(generics.CreateAPIView):
    """
    POST /api/v1/polls/create/
    ISCOOA Executive creates a new poll.
    """
    serializer_class   = PollCreateSerializer
    permission_classes = [IsIscooaExec]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = serializer.save(created_by=request.user)
        return Response(
            {
                'detail':   'Poll created successfully.',
                'poll_ref': poll.poll_ref,
                'question': poll.question,
                'status':   poll.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Polls'])
class AllPollsView(generics.ListAPIView):
    """
    GET /api/v1/polls/all/
    ISCOOA Executive sees all polls including drafts.
    Filter by ?status=active|closed|draft
    """
    serializer_class   = PollListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Poll.objects.all()
        poll_status = self.request.query_params.get('status')
        if poll_status:
            qs = qs.filter(status=poll_status)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=['Polls'])
class PollAdminDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/polls/all/<id>/
    ISCOOA Executive views full poll detail.
    """
    serializer_class   = PollSerializer
    permission_classes = [IsIscooaExec]
    queryset           = Poll.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(tags=['Polls'])
class ClosePollView(APIView):
    """
    POST /api/v1/polls/<id>/close/
    ISCOOA Executive closes a poll manually.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            poll = Poll.objects.get(pk=pk)
        except Poll.DoesNotExist:
            return Response(
                {'detail': 'Poll not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if poll.status == Poll.Status.CLOSED:
            return Response(
                {'detail': 'Poll is already closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        poll.status    = Poll.Status.CLOSED
        poll.closes_at = timezone.now()
        poll.save()

        return Response({
            'detail':           'Poll closed successfully.',
            'poll_ref':         poll.poll_ref,
            'final_yes_count':  poll.yes_count,
            'final_no_count':   poll.no_count,
            'total_votes':      poll.total_votes,
            'yes_percentage':   poll.yes_percentage,
            'no_percentage':    poll.no_percentage,
            'participation_rate': poll.participation_rate,
        })


@extend_schema(tags=['Polls'])
class PublishPollView(APIView):
    """
    POST /api/v1/polls/<id>/publish/
    ISCOOA Executive publishes a draft poll
    making it active for operators to vote.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            poll = Poll.objects.get(pk=pk)
        except Poll.DoesNotExist:
            return Response(
                {'detail': 'Poll not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if poll.status != Poll.Status.DRAFT:
            return Response(
                {'detail': f'Only draft polls can be published. This poll is {poll.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        poll.status   = Poll.Status.ACTIVE
        poll.opens_at = timezone.now()
        poll.save()

        return Response({
            'detail':   'Poll published and now active.',
            'poll_ref': poll.poll_ref,
            'status':   poll.status,
            'opens_at': poll.opens_at,
        })