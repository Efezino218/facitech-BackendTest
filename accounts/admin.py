from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserChangeForm(forms.ModelForm):
    """
    Custom form for editing users in Django Admin.
    Safely handles the access JSONField which can be None
    for users created before the default was enforced.
    """

    class Meta:
        model  = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Safely coerce access field to list if it is None
        if self.instance and self.instance.pk:
            if self.instance.access is None:
                self.instance.access = []
                # Fix it in the initial data too so the form renders correctly
                if 'access' in self.initial:
                    self.initial['access'] = []

    def clean_access(self):
        """Ensure access is always a list, never None."""
        value = self.cleaned_data.get('access')
        if value is None:
            return []
        if isinstance(value, str):
            # Handle case where someone types raw JSON
            import json
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return value


class UserCreationForm(forms.ModelForm):
    """
    Custom form for creating users in Django Admin.
    Sets access to empty list by default.
    """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model  = User
        fields = (
            'email', 'first_name', 'last_name',
            'phone', 'association', 'role', 'ipos',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.access = []  # Always start with empty list
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form     = UserChangeForm
    add_form = UserCreationForm

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
    ordering = ('email',)

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
                'association', 'role', 'ipos',
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        """
        Extra safety net — ensure access is never saved as None.
        """
        if obj.access is None:
            obj.access = []
        super().save_model(request, obj, form, change)