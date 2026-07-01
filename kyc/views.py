from urllib import request
import uuid
from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from audit.models import log_action

from .models import (
    KYCApplication, KYCReviewNote, KYCPersonal, KYCBusiness,
    KYCShop, KYCIscooaStanding, KYCStaff, KYCNextOfKin,
    KYCGuarantor, KYCFinance, KYCEmergencyContact,
    KYCDocuments, KYCDeclaration, KYCStatus
)
from .serializers import (
    KYCApplicationSerializer, KYCApplicationListSerializer,
    KYCPersonalSerializer, KYCBusinessSerializer, KYCShopSerializer,
    KYCIscooaStandingSerializer, KYCStaffSerializer, KYCNextOfKinSerializer,
    KYCGuarantorSerializer, KYCFinanceSerializer, KYCEmergencyContactSerializer,
    KYCDocumentsSerializer, KYCDeclarationSerializer,
)
from .permissions import IsOperator, IsIscooaExec
from drf_spectacular.utils import extend_schema


def generate_kyc_id():
    """Generate a sequential KYC ID like KYC-001."""
    count = KYCApplication.objects.count() + 1
    return f"KYC-{count:03d}"


# ─── OPERATOR VIEWS ───────────────────────────────────────────────────────────

@extend_schema(tags=['KYC'])
class KYCStartView(APIView):
    """
    POST /api/v1/kyc/start/
    Operator starts a new KYC application.
    Status starts as DRAFT — not submitted yet.
    Only moves to SUBMITTED after Step 11 declaration.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        if hasattr(request.user, 'kyc_application'):
            return Response(
                {'detail': 'You already have a KYC application.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        application = KYCApplication.objects.create(
            operator    = request.user,
            kyc_id      = generate_kyc_id(),
            status      = KYCStatus.DRAFT,           # ← changed from SUBMITTED
            association = request.user.association,
        )
        return Response(
            {
                'kyc_id':  application.kyc_id,
                'id':      str(application.id),
                'status':  application.status,
                'message': 'KYC application started. Please complete all 11 steps then submit.',
            },
            status=status.HTTP_201_CREATED
        )

@extend_schema(tags=['KYC'])
class KYCMyApplicationView(APIView):
    """
    GET /api/v1/kyc/my-application/
    Operator retrieves their own full KYC record.
    """
    permission_classes = [IsOperator]

    def get(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found. Please start one first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = KYCApplicationSerializer(application)
        return Response(serializer.data)


@extend_schema(tags=['KYC'])
class KYCStepPersonalView(APIView):
    """
    POST /api/v1/kyc/step/personal/
    Operator submits Step 1 — Personal Identity.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCPersonal.objects.get_or_create(application=application)
        serializer = KYCPersonalSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepBusinessView(APIView):
    """
    POST /api/v1/kyc/step/business/
    Operator submits Step 2 — Business Profile.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCBusiness.objects.get_or_create(application=application)
        serializer = KYCBusinessSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepShopsView(APIView):
    """
    POST /api/v1/kyc/step/shops/
    Operator submits Step 3 — Shops.
    Accepts a list of shop records. Replaces existing shops for this application.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        shops_data = request.data if isinstance(request.data, list) else [request.data]

        # Clear existing shops and re-save fresh
        KYCShop.objects.filter(application=application).delete()

        created_shops = []
        for shop_data in shops_data:
            serializer = KYCShopSerializer(data=shop_data)
            if serializer.is_valid():
                serializer.save(application=application)
                created_shops.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(created_shops, status=status.HTTP_200_OK)


@extend_schema(tags=['KYC'])
class KYCStepIscooaStandingView(APIView):
    """POST /api/v1/kyc/step/iscooa-standing/ — Step 4"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCIscooaStanding.objects.get_or_create(application=application)
        serializer = KYCIscooaStandingSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepStaffView(APIView):
    """POST /api/v1/kyc/step/staff/ — Step 5"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCStaff.objects.get_or_create(application=application)
        serializer = KYCStaffSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepNextOfKinView(APIView):
    """POST /api/v1/kyc/step/next-of-kin/ — Step 6"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCNextOfKin.objects.get_or_create(application=application)
        serializer = KYCNextOfKinSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepGuarantorView(APIView):
    """POST /api/v1/kyc/step/guarantor/ — Step 7"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCGuarantor.objects.get_or_create(application=application)
        serializer = KYCGuarantorSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepFinanceView(APIView):
    """POST /api/v1/kyc/step/finance/ — Step 8"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCFinance.objects.get_or_create(application=application)
        serializer = KYCFinanceSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepEmergencyContactView(APIView):
    """POST /api/v1/kyc/step/emergency-contact/ — Step 9"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCEmergencyContact.objects.get_or_create(application=application)
        serializer = KYCEmergencyContactSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepDocumentsView(APIView):
    """POST /api/v1/kyc/step/documents/ — Step 10"""
    permission_classes = [IsOperator]

    def post(self, request):
        application = request.user.kyc_application
        instance, _ = KYCDocuments.objects.get_or_create(application=application)
        serializer = KYCDocumentsSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['KYC'])
class KYCStepDeclarationView(APIView):
    """
    POST /api/v1/kyc/step/declaration/
    Step 11 — Final submission.
    This is the ONLY place status moves to SUBMITTED.
    """
    permission_classes = [IsOperator]

    def post(self, request):
        try:
            application = request.user.kyc_application
        except KYCApplication.DoesNotExist:
            return Response(
                {'detail': 'No KYC application found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Block resubmission if already submitted or approved
        if application.status in [KYCStatus.SUBMITTED, KYCStatus.APPROVED]:
            return Response(
                {'detail': f'Your application is already {application.status}. You cannot resubmit.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Confirm operator has accepted both consents before anything else
        ndpr        = request.data.get('ndpr_consent', False)
        declaration = request.data.get('declaration', False)

        if not ndpr or not declaration:
            return Response(
                {
                    'detail': (
                        'You must accept the NDPR consent and declaration '
                        'before submitting your application.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save declaration step
        instance, _ = KYCDeclaration.objects.get_or_create(application=application)
        serializer  = KYCDeclarationSerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # NOW move status to submitted
        application.status = KYCStatus.SUBMITTED
        application.save()

        return Response({
            'detail':  'KYC application submitted successfully. ISCOOA will review within 48 hours.',
            'kyc_id':  application.kyc_id,
            'status':  application.status,
        })
# ─── ISCOOA EXECUTIVE VIEWS ───────────────────────────────────────────────────

@extend_schema(tags=['KYC'])
class KYCQueueView(generics.ListAPIView):
    """
    GET /api/v1/kyc/queue/
    ISCOOA Executive sees all KYC applications.
    DRAFT applications are excluded — they are not submitted yet.
    Filter by status using ?status=submitted|docs_requested|approved|rejected
    """
    serializer_class   = KYCApplicationListSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        # Never show drafts, and only show this exec's own association
        qs = KYCApplication.objects.exclude(
            status=KYCStatus.DRAFT
        ).filter(
            operator__association = self.request.user.association
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                operator__email__icontains=search
            ) | qs.filter(
                operator__first_name__icontains=search
            ) | qs.filter(
                operator__last_name__icontains=search
            )
        return qs


@extend_schema(tags=['KYC'])
class KYCDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/kyc/<id>/
    Association Executive views full KYC record —
    scoped to their own association.
    """
    serializer_class   = KYCApplicationSerializer
    permission_classes = [IsIscooaExec]

    def get_queryset(self):
        return KYCApplication.objects.filter(
            operator__association = self.request.user.association
        )


@extend_schema(tags=['KYC'])
class KYCApproveView(APIView):
    """
    POST /api/v1/kyc/<id>/approve/
    ISCOOA Executive approves a KYC application.
    Auto-assigns a member number.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            application = KYCApplication.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except KYCApplication.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if application.status == KYCStatus.APPROVED:
            return Response({'detail': 'Already approved.'}, status=status.HTTP_400_BAD_REQUEST)


        # Generate member number dynamically from association config
        count = KYCApplication.objects.filter(status=KYCStatus.APPROVED).count() + 1
        try:
            config = application.operator.association.config
            member_number = config.generate_member_number(count)
        except Exception:
            # Fallback if no association config found
            from django.utils import timezone
            year = timezone.now().year
            member_number = f"MEMBER-{year}-{count:04d}"


        with transaction.atomic():
            from django.utils import timezone
            application.status        = KYCStatus.APPROVED
            application.member_number = member_number
            application.approved_by   = request.user
            application.approved_date = timezone.now()
            application.save()

            # Also update the operator's user record
            application.operator.member_number = member_number
            application.operator.save()

            note = request.data.get('note', 'Application approved.')
            KYCReviewNote.objects.create(
                application=application,
                reviewed_by=request.user,
                note=note,
            )

            
            log_action(
                user        = request.user,
                action      = 'approve',
                table_name  = 'kyc_applications',
                record_id   = str(application.id),
                record_ref  = application.kyc_id,
                description = f'KYC approved for {application.operator.email}. Member number: {member_number}',
                request     = request,
            )



        with transaction.atomic():
            application.status        = KYCStatus.APPROVED
            application.member_number = member_number
            application.approved_by   = request.user
            application.approved_date = timezone.now()
            application.save()

            # Also update the operator's user record
            application.operator.member_number = member_number
            application.operator.save()

            note = request.data.get('note', 'Application approved.')
            KYCReviewNote.objects.create(
                application=application,
                reviewed_by=request.user,
                note=note,
            )

            # ── Start free trial from approval date ──────────────────
            from subscriptions.models import Subscription
            from shops.models import Shop

            shop_count = Shop.objects.filter(
                operator  = application.operator,
                is_active = True
            ).count() or 1

            # Get subscription rate from association config
            default_rate = 100000
            try:
                default_rate = application.operator.association.config.subscription_rate
            except Exception:
                pass

            # Set the trial start date to TODAY (approval date)
            # Billing Month 2 starts one month from today
            import datetime
            trial_start  = timezone.now().date()
            billing_date = trial_start + datetime.timedelta(days=30)

            Subscription.objects.update_or_create(
                operator = application.operator,
                defaults = {
                    'status':        Subscription.Status.KYC,
                    'current_month': 1,
                    'shop_count':    shop_count,
                    'rate_per_shop': default_rate,
                    'period_start':  trial_start,
                    'renewal_date':  billing_date,
                }
            )

            from audit.models import log_action
            log_action(
                user        = request.user,
                action      = 'approve',
                table_name  = 'kyc_applications',
                record_id   = str(application.id),
                record_ref  = application.kyc_id,
                description = f'KYC approved for {application.operator.email}. Member number: {member_number}',
                request     = request,
            )

        return Response({
            'detail': 'KYC approved.',
            'member_number': member_number,
        })


@extend_schema(tags=['KYC'])
class KYCRequestDocsView(APIView):
    """
    POST /api/v1/kyc/<id>/request-docs/
    ISCOOA Executive requests additional documents.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            application = KYCApplication.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except KYCApplication.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        note = request.data.get('note', '')
        if not note:
            return Response(
                {'detail': 'A note explaining what documents are needed is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status    = KYCStatus.DOCS_REQUESTED
        application.docs_note = note
        application.save()

        KYCReviewNote.objects.create(
            application=application,
            reviewed_by=request.user,
            note=f"[DOCS REQUESTED] {note}",
        )

        return Response({'detail': 'Documents requested.', 'status': application.status})


@extend_schema(tags=['KYC'])
class KYCRejectView(APIView):
    """
    POST /api/v1/kyc/<id>/reject/
    ISCOOA Executive rejects a KYC application.
    """
    permission_classes = [IsIscooaExec]

    def post(self, request, pk):
        try:
            application = KYCApplication.objects.get(
                pk = pk,
                operator__association = request.user.association,
            )
        except KYCApplication.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        note = request.data.get('note', '')
        if not note:
            return Response(
                {'detail': 'A rejection reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = KYCStatus.REJECTED
        application.save()

        KYCReviewNote.objects.create(
            application=application,
            reviewed_by=request.user,
            note=f"[REJECTED] {note}",
        )

        return Response({'detail': 'Application rejected.', 'status': application.status})