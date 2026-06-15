from rest_framework import serializers
from .models import Poll, Vote


class PollSerializer(serializers.ModelSerializer):
    """
    Full poll serializer with live tallies.
    Also shows whether the current operator has voted.
    """
    created_by_name  = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    total_votes      = serializers.ReadOnlyField()
    yes_percentage   = serializers.ReadOnlyField()
    no_percentage    = serializers.ReadOnlyField()
    participation_rate = serializers.ReadOnlyField()

    # Whether the requesting operator has voted
    my_vote          = serializers.SerializerMethodField()

    class Meta:
        model  = Poll
        fields = [
            'id', 'poll_ref', 'question', 'description',
            'status', 'created_by', 'created_by_name',
            'opens_at', 'closes_at', 'target_count',
            'yes_count', 'no_count', 'total_votes',
            'yes_percentage', 'no_percentage',
            'participation_rate', 'my_vote',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'poll_ref', 'created_by',
            'yes_count', 'no_count',
            'created_at', 'updated_at',
        ]

    def get_my_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = Vote.objects.get(poll=obj, operator=request.user)
            return vote.choice
        except Vote.DoesNotExist:
            return None


class PollCreateSerializer(serializers.ModelSerializer):
    """Used by ISCOOA Executive to create a new poll."""
    class Meta:
        model  = Poll
        fields = [
            'question', 'description',
            'opens_at', 'closes_at',
            'target_count', 'status',
        ]


class PollListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing polls."""
    total_votes      = serializers.ReadOnlyField()
    yes_percentage   = serializers.ReadOnlyField()
    no_percentage    = serializers.ReadOnlyField()
    my_vote          = serializers.SerializerMethodField()

    class Meta:
        model  = Poll
        fields = [
            'id', 'poll_ref', 'question',
            'status', 'yes_count', 'no_count',
            'total_votes', 'yes_percentage', 'no_percentage',
            'closes_at', 'my_vote',
        ]

    def get_my_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = Vote.objects.get(poll=obj, operator=request.user)
            return vote.choice
        except Vote.DoesNotExist:
            return None


class CastVoteSerializer(serializers.Serializer):
    """Used by operator to cast a vote."""
    choice = serializers.ChoiceField(choices=Vote.Choice.choices)