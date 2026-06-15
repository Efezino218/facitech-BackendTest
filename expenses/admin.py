from django.contrib import admin
from .models import Expense, ExpenseApprovalStep


class ExpenseApprovalStepInline(admin.TabularInline):
    model         = ExpenseApprovalStep
    extra         = 0
    readonly_fields = (
        'step_number', 'role', 'actor',
        'status', 'note', 'acted_at', 'created_at'
    )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display    = (
        'expense_ref', 'title', 'category',
        'amount', 'status', 'requires_bot',
        'raised_by', 'raised_date'
    )
    list_filter     = ('status', 'category', 'requires_bot')
    search_fields   = ('expense_ref', 'title', 'raised_by__email')
    readonly_fields = (
        'expense_ref', 'requires_bot',
        'raised_date', 'created_at', 'updated_at'
    )
    inlines         = [ExpenseApprovalStepInline]


@admin.register(ExpenseApprovalStep)
class ExpenseApprovalStepAdmin(admin.ModelAdmin):
    list_display  = (
        'expense', 'step_number', 'role',
        'actor', 'status', 'acted_at'
    )
    list_filter   = ('status', 'role')
    readonly_fields = ('created_at',)