from rest_framework import serializers
from .models import Resolution, ResolutionVote, AdvisoryNote


class ResolutionVoteSerializer(serializers.ModelSerializer):
    bot_member_name = serializers.CharField(
        source='bot_member.full_name', read_only=True
    )

    class Meta:
        model  = ResolutionVote
        fields = [
            'id', 'bot_member', 'bot_member_name',
            'choice', 'note', 'voted_at',
        ]
        read_only_fields = ['id', 'bot_member', 'voted_at']


class AdvisoryNoteSerializer(serializers.ModelSerializer):
    advisor_name = serializers.CharField(
        source='advisor.full_name', read_only=True
    )
    advisor_email = serializers.EmailField(
        source='advisor.email', read_only=True
    )

    class Meta:
        model  = AdvisoryNote
        fields = [
            'id', 'advisor', 'advisor_name',
            'advisor_email', 'note', 'submitted_at',
        ]
        read_only_fields = ['id', 'advisor', 'submitted_at']


class ResolutionSerializer(serializers.ModelSerializer):
    """Full resolution serializer."""
    proposed_by_name    = serializers.CharField(
        source='proposed_by.full_name', read_only=True
    )
    status_display      = serializers.CharField(
        source='get_status_display', read_only=True
    )
    total_votes         = serializers.ReadOnlyField()
    is_passed           = serializers.ReadOnlyField()
    votes               = ResolutionVoteSerializer(many=True, read_only=True)
    advisory_notes      = AdvisoryNoteSerializer(many=True, read_only=True)

    # Whether current BOT member has voted
    my_vote             = serializers.SerializerMethodField()

    # Whether current advisor has submitted a note
    my_note             = serializers.SerializerMethodField()

    class Meta:
        model  = Resolution
        fields = [
            'id', 'res_ref', 'title', 'full_text',
            'status', 'status_display',
            'proposed_by', 'proposed_by_name', 'proposed_date',
            'yea_count', 'nay_count', 'abstain_count',
            'total_votes', 'is_passed',
            'ratified_date', 'signatories', 'resolution_note',
            'votes', 'advisory_notes',
            'my_vote', 'my_note',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'res_ref',
            'yea_count', 'nay_count', 'abstain_count',
            'ratified_date', 'signatories',
            'created_at', 'updated_at',
        ]

    def get_my_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = ResolutionVote.objects.get(
                resolution = obj,
                bot_member = request.user
            )
            return vote.choice
        except ResolutionVote.DoesNotExist:
            return None

    def get_my_note(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            note = AdvisoryNote.objects.get(
                resolution = obj,
                advisor    = request.user
            )
            return note.note
        except AdvisoryNote.DoesNotExist:
            return None


class ResolutionCreateSerializer(serializers.ModelSerializer):
    """Used to create or update a resolution."""
    class Meta:
        model  = Resolution
        fields = [
            'title', 'full_text',
            'proposed_date', 'status',
        ]


class ResolutionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing resolutions."""
    proposed_by_name = serializers.CharField(
        source='proposed_by.full_name', read_only=True
    )
    total_votes      = serializers.ReadOnlyField()

    class Meta:
        model  = Resolution
        fields = [
            'id', 'res_ref', 'title',
            'status', 'proposed_by_name',
            'proposed_date', 'yea_count',
            'nay_count', 'abstain_count',
            'total_votes', 'ratified_date',
            'created_at',
        ]


class CastResolutionVoteSerializer(serializers.Serializer):
    """Used by BOT member to vote on a resolution."""
    choice = serializers.ChoiceField(choices=ResolutionVote.Choice.choices)
    note   = serializers.CharField(required=False, allow_blank=True)


class SubmitAdvisoryNoteSerializer(serializers.Serializer):
    """Used by Advisor to submit a note on a resolution."""
    note = serializers.CharField()