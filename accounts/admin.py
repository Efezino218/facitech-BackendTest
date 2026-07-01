from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = (
        'email', 'full_name', 'role', 'ipos',
        'association', 'member_number', 'is_active'
    )
    list_filter   = ('role', 'ipos', 'is_active', 'association')
    search_fields = (
        'email', 'first_name', 'last_name',
        'member_number', 'username',
        'association__name', 'association__slug',
    )
    ordering      = ('email',)

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal', {
            'fields': ('first_name', 'last_name', 'phone', 'username')
        }),
        ('Association', {
            'fields': ('association',),
            'description': 'Which association this user belongs to.',
        }),
        ('Role & Access', {
            'fields': ('role', 'ipos', 'access', 'member_number')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'first_name', 'last_name', 'phone',
                'association',
                'role', 'ipos',
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')