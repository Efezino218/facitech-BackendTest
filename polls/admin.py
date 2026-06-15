from django.contrib import admin
from .models import Poll, Vote


class VoteInline(admin.TabularInline):
    model         = Vote
    extra         = 0
    readonly_fields = ('operator', 'choice', 'voted_at')


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display    = (
        'poll_ref', 'question', 'status',
        'yes_count', 'no_count', 'total_votes',
        'closes_at', 'created_at'
    )
    list_filter     = ('status',)
    search_fields   = ('poll_ref', 'question')
    readonly_fields = (
        'poll_ref', 'yes_count', 'no_count',
        'created_at', 'updated_at'
    )
    inlines         = [VoteInline]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display  = ('poll', 'operator', 'choice', 'voted_at')
    list_filter   = ('choice',)
    search_fields = ('poll__poll_ref', 'operator__email')
    readonly_fields = ('voted_at',)