from django.contrib import admin
from .models import Resolution, ResolutionVote, AdvisoryNote


class ResolutionVoteInline(admin.TabularInline):
    model         = ResolutionVote
    extra         = 0
    readonly_fields = ('bot_member', 'choice', 'note', 'voted_at')


class AdvisoryNoteInline(admin.TabularInline):
    model         = AdvisoryNote
    extra         = 0
    readonly_fields = ('advisor', 'note', 'submitted_at')


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display    = (
        'res_ref', 'title', 'status',
        'yea_count', 'nay_count', 'abstain_count',
        'proposed_by', 'proposed_date', 'created_at'
    )
    list_filter     = ('status',)
    search_fields   = ('res_ref', 'title', 'full_text')
    readonly_fields = ('res_ref', 'created_at', 'updated_at')
    inlines         = [ResolutionVoteInline, AdvisoryNoteInline]


@admin.register(ResolutionVote)
class ResolutionVoteAdmin(admin.ModelAdmin):
    list_display  = ('resolution', 'bot_member', 'choice', 'voted_at')
    list_filter   = ('choice',)
    readonly_fields = ('voted_at',)


@admin.register(AdvisoryNote)
class AdvisoryNoteAdmin(admin.ModelAdmin):
    list_display  = ('resolution', 'advisor', 'submitted_at')
    readonly_fields = ('submitted_at',)