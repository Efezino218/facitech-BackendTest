from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Shop, StaffMember
from .serializers import (
    ShopSerializer, ShopListSerializer,
    ShopCreateSerializer, StaffMemberSerializer
)
from .permissions import IsOperator, IsIscooaExec, IsOperatorOrIscooaExec
from drf_spectacular.utils import extend_schema


# ─── OPERATOR SHOP VIEWS ──────────────────────────────────────────────────────

@extend_schema(tags=['Shop'])
class MyShopsView(generics.ListAPIView):
    """
    GET /api/v1/shops/my-shops/
    Operator sees all their own shops.
    """
    serializer_class   = ShopSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return Shop.objects.filter(
            operator=self.request.user,
            is_active=True
        )


@extend_schema(tags=['Shop'])
class ShopCreateView(generics.CreateAPIView):
    """
    POST /api/v1/shops/create/
    Operator registers a new shop.
    """
    serializer_class   = ShopCreateSerializer
    permission_classes = [IsOperator]

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)


@extend_schema(tags=['Shop'])
class ShopDetailView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/shops/<id>/
    PUT  /api/v1/shops/<id>/
    Operator views or updates their own shop.
    """
    permission_classes = [IsOperator]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ShopCreateSerializer
        return ShopSerializer

    def get_queryset(self):
        return Shop.objects.filter(operator=self.request.user)


# ─── STAFF VIEWS (Operator manages their own staff) ───────────────────────────

@extend_schema(tags=['Shop'])
class MyStaffView(generics.ListAPIView):
    """
    GET /api/v1/shops/my-staff/
    Operator sees all their registered staff.
    """
    serializer_class   = StaffMemberSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return StaffMember.objects.filter(operator=self.request.user)


@extend_schema(tags=['Shop'])
class StaffCreateView(APIView):
    """
    POST /api/v1/shops/my-staff/add/
    Operator registers a new staff member.
    Max 5 staff enforced here.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        # Enforce 5 staff limit
        current_count = StaffMember.objects.filter(
            operator=request.user,
            is_active=True
        ).count()

        if current_count >= 5:
            return Response(
                {'detail': 'You have reached the maximum of 5 staff members on the Basic tier.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Confirm the shop belongs to this operator
        shop_id = request.data.get('shop')
        try:
            shop = Shop.objects.get(id=shop_id, operator=request.user)
        except Shop.DoesNotExist:
            return Response(
                {'detail': 'Shop not found or does not belong to you.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = StaffMemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(operator=request.user, shop=shop)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Shop'])
class StaffDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/shops/my-staff/<id>/
    PUT    /api/v1/shops/my-staff/<id>/
    DELETE /api/v1/shops/my-staff/<id>/
    Operator manages a specific staff member.
    """
    serializer_class   = StaffMemberSerializer
    permission_classes = [IsOperator]

    def get_queryset(self):
        return StaffMember.objects.filter(operator=self.request.user)

    def perform_destroy(self, instance):
        # Soft delete — mark inactive instead of hard delete
        instance.is_active = False
        instance.save()


# ─── ISCOOA EXECUTIVE SHOP VIEWS ──────────────────────────────────────────────

@extend_schema(tags=['Shop'])
class AllShopsView(generics.ListAPIView):
    """
    GET /api/v1/shops/all/
    ISCOOA Executive sees all registered shops.
    Filter by block using ?block=A|B|C etc.
    Filter by operator using ?operator=<email>
    """
    serializer_class   = ShopListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        qs = Shop.objects.all()
        block = self.request.query_params.get('block')
        if block:
            qs = qs.filter(block=block)
        operator_email = self.request.query_params.get('operator')
        if operator_email:
            qs = qs.filter(operator__email__icontains=operator_email)
        return qs


@extend_schema(tags=['Shop'])
class ShopAdminDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/shops/all/<id>/
    ISCOOA Executive views full detail of any shop.
    """
    serializer_class   = ShopSerializer
    permission_classes = [IsIscooaExec]
    queryset           = Shop.objects.all()