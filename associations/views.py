from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Association, AssociationConfig
from .serializers import (
    AssociationSerializer,
    AssociationCreateSerializer,
    AssociationConfigSerializer,
    PublicAssociationConfigSerializer,
)
from .permissions import IsSuperAdmin
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Associations'])
class AssociationListView(generics.ListAPIView):
    """
    GET /api/v1/associations/
    Super Admin sees all associations on the platform.
    """
    serializer_class   = AssociationSerializer
    permission_classes = [IsSuperAdmin]
    queryset           = Association.objects.all()


@extend_schema(tags=['Associations'])
class AssociationCreateView(generics.CreateAPIView):
    """
    POST /api/v1/associations/create/
    Super Admin creates a new association.
    Also creates the AssociationConfig record.
    """
    serializer_class   = AssociationCreateSerializer
    permission_classes = [IsSuperAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        association = serializer.save()
        return Response(
            {
                'detail':   'Association created successfully.',
                'id':       str(association.id),
                'name':     association.name,
                'slug':     association.slug,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Associations'])
class AssociationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/associations/<id>/
    PUT /api/v1/associations/<id>/
    Super Admin views or updates an association.
    """
    permission_classes = [IsSuperAdmin]
    queryset           = Association.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AssociationCreateSerializer
        return AssociationSerializer


@extend_schema(tags=['Associations'])
class UpdateAssociationConfigView(generics.UpdateAPIView):
    """
    PUT /api/v1/associations/<id>/config/
    Super Admin updates association config.
    """
    serializer_class   = AssociationConfigSerializer
    permission_classes = [IsSuperAdmin]

    def get_object(self):
        association = Association.objects.get(pk=self.kwargs['pk'])
        return association.config


@extend_schema(tags=['Associations'])
class PublicConfigView(APIView):
    """
    GET /api/v1/associations/config/<slug>/
    PUBLIC endpoint — no auth required.
    Frontend calls this on startup to get branding.
    Returns association name, logo, colors, footer text.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            association = Association.objects.get(slug=slug, is_active=True)
            config      = association.config
        except Association.DoesNotExist:
            return Response(
                {'detail': f'Association "{slug}" not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AssociationConfig.DoesNotExist:
            return Response(
                {'detail': 'Association configuration not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PublicAssociationConfigSerializer(config)
        return Response(serializer.data)


@extend_schema(tags=['Associations'])
class AssociationStatsView(APIView):
    """
    GET /api/v1/associations/<id>/stats/
    Super Admin sees stats for a specific association.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            association = Association.objects.get(pk=pk)
        except Association.DoesNotExist:
            return Response(
                {'detail': 'Association not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from accounts.models import User
        from kyc.models import KYCApplication
        from subscriptions.models import SubscriptionPayment
        from adverts.models import Advert
        from django.db.models import Sum

        operators = User.objects.filter(
            association = association,
            role        = 'op',
            is_active   = True
        ).count()

        approved_members = KYCApplication.objects.filter(
            operator__association = association,
            status                = 'approved'
        ).count()

        sub_revenue = SubscriptionPayment.objects.filter(
            operator__association = association,
            status                = 'paid'
        ).aggregate(
            total=Sum('iscooa_cut')
        )['total'] or 0

        advert_revenue = Advert.objects.filter(
            operator__association = association,
            status                = 'approved'
        ).aggregate(
            total=Sum('iscooa_cut')
        )['total'] or 0

        return Response({
            'association':       association.name,
            'total_operators':   operators,
            'approved_members':  approved_members,
            'association_revenue_naira': (sub_revenue + advert_revenue) / 100,
        })



@extend_schema(tags=['Associations'])
class PublicAssociationListView(APIView):
    """
    GET /api/v1/associations/public/
    PUBLIC endpoint — no auth required.
    Returns a simple list of all active associations.
    Used for the registration page dropdown.
    Only returns slug, name and logo_url.
    No financial data exposed.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        associations = Association.objects.filter(
            is_active=True
        ).select_related('config').order_by('name')

        data = [
            {
                'slug':     assoc.slug,
                'name':     assoc.name,
                'logo_url': assoc.config.logo_url if hasattr(assoc, 'config') else '',
            }
            for assoc in associations
        ]

        return Response({
            'count':        len(data),
            'associations': data,
        })