from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Role, ExcoPosition


class UserSerializer(serializers.ModelSerializer):
    full_name           = serializers.ReadOnlyField()
    association_id      = serializers.UUIDField(source='association.id', read_only=True)
    association_name    = serializers.CharField(source='association.name', read_only=True)
    association_slug    = serializers.CharField(source='association.slug', read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone', 'role', 'ipos', 'access', 'member_number',
            'full_name', 'is_active', 'created_at',
            'association_id', 'association_name', 'association_slug',
        ]
        read_only_fields = ['id', 'member_number', 'created_at']


class OperatorRegisterSerializer(serializers.ModelSerializer):
    """
    PUBLIC registration endpoint.
    Only operators can self-register.
    Any attempt to register as a privileged role
    is rejected with a clear error message.
    """
    password         = serializers.CharField(write_only=True, min_length=6)
    role             = serializers.CharField(required=False, write_only=True)
    ipos             = serializers.CharField(required=False, write_only=True)
    association_slug = serializers.CharField(required=False, write_only=True)

    class Meta:
        model  = User
        fields = [
            'email', 'password',
            'first_name', 'last_name', 'phone',
            'role', 'ipos', 'association_slug',
        ]

    def validate(self, data):
        role = data.get('role', None)
        ipos = data.get('ipos', None)

        # Reject any attempt to register as a privileged role
        if role and role != 'op':
            raise serializers.ValidationError(
                {
                    'role': (
                        f'You cannot self-register as "{role}". '
                        'The public registration endpoint is for operators only. '
                        'Privileged accounts (Exco, BOT, Advisor) are created '
                        'by the President or Super Admin.'
                    )
                }
            )

        # Strip role and ipos before saving
        # We do not want these stored even if op was passed
        data.pop('role', None)
        data.pop('ipos', None)
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        slug     = validated_data.pop('association_slug', None)

        user = User(
            role = Role.OPERATOR,
            ipos = ExcoPosition.NONE,
            **validated_data
        )
        user.set_password(password)

        # Link to association if slug provided
        if slug:
            try:
                from associations.models import Association
                user.association = Association.objects.get(
                    slug      = slug,
                    is_active = True
                )
            except Exception:
                pass

        user.save()
        return user


class PrivilegedAccountCreateSerializer(serializers.ModelSerializer):
    """
    PROTECTED endpoint — President or Super Admin only.
    Used to create Exco, BOT, Advisor and Super Admin accounts.
    Role must be explicitly provided and validated.
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model  = User
        fields = [
            'email', 'password',
            'first_name', 'last_name', 'phone',
            'role', 'ipos',
        ]

    def validate_role(self, value):
        # Operator accounts cannot be created via this endpoint
        # Operators must self-register
        if value == Role.OPERATOR:
            raise serializers.ValidationError(
                'Operators must self-register via the public registration endpoint.'
            )
        return value

    def validate(self, data):
        role = data.get('role')
        ipos = data.get('ipos', ExcoPosition.NONE)

        # ISCOOA Exec must have a valid position
        if role == Role.ISCOOA_EXEC:
            valid_positions = [
                ExcoPosition.PRESIDENT,
                ExcoPosition.VICE_PRESIDENT,
                ExcoPosition.SECRETARY_GENERAL,
                ExcoPosition.TREASURER,
                ExcoPosition.LEGAL_ADVISER,
                ExcoPosition.PRO,
            ]
            if ipos not in valid_positions:
                raise serializers.ValidationError(
                    f'ISCOOA Exec accounts must have a valid position. '
                    f'Valid positions: {[p for p in valid_positions]}'
                )
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom login serializer.
    Adds user role, name and KYC status to the JWT response.
    Blocks inactive accounts from logging in.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Check account is active
        if not self.user.is_active:
            raise serializers.ValidationError(
                'Your account has been deactivated. '
                'Please contact ISCOOA administration.'
            )

        # Check KYC status for operators
        kyc_status = None
        if self.user.role == Role.OPERATOR:
            try:
                kyc_status = self.user.kyc_application.status
            except Exception:
                kyc_status = 'not_started'

        # Association data
        association_data = None
        if self.user.association:
            association_data = {
                'id':   str(self.user.association.id),
                'name': self.user.association.name,
                'slug': self.user.association.slug,
            }

        data['user'] = {
            'id':            str(self.user.id),
            'email':         self.user.email,
            'full_name':     self.user.full_name,
            'role':          self.user.role,
            'ipos':          self.user.ipos,
            'access':        self.user.access,
            'member_number': self.user.member_number,
            'kyc_status':    kyc_status,
            'association':   association_data,
        }
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Used by any authenticated user to change their password."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                'Old password is incorrect.'
            )
        return value


class DeactivateAccountSerializer(serializers.Serializer):
    """Used by President or Super Admin to deactivate an account."""
    reason = serializers.CharField()