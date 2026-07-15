from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from associations.models import Association
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Overview'])
class OperatorOverviewView(APIView):
    """
    GET /api/v1/overview/operator/
    Operator home dashboard.
    All counts are scoped to this specific operator only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'op':
            return Response(
                {'detail': 'This overview is for operators only.'},
                status=403
            )

        from shops.models import Shop
        from bills.models import Bill
        from subscriptions.models import Subscription
        from wallet.models import Wallet
        from notifications.models import Notification
        from adverts.models import Advert
        from disputes.models import Dispute

        # ── Shops ─────────────────────────────────────────────────────
        shops = Shop.objects.filter(operator=user, is_active=True)
        shop_count = shops.count()

        # ── Bills ─────────────────────────────────────────────────────
        # Only THIS operator's unpaid bills
        outstanding_bills = Bill.objects.filter(
            operator = user,
            status   = 'unpaid'
        )
        outstanding_count  = outstanding_bills.count()
        outstanding_amount = outstanding_bills.aggregate(
            total=Sum('total')
        )['total'] or 0

        # ── Wallet ────────────────────────────────────────────────────
        try:
            wallet          = user.wallet
            balance         = wallet.balance_naira
            coolmfb_account = wallet.coolmfb_account_number
        except Exception:
            balance         = 0
            coolmfb_account = None

        # ── Subscription ──────────────────────────────────────────────
        try:
            subscription = user.subscription
            sub_status   = subscription.status
            sub_month    = subscription.current_month
            monthly_fee  = subscription.monthly_fee_naira
            renewal_date = subscription.renewal_date
        except Exception:
            sub_status   = 'kyc'
            sub_month    = 1
            monthly_fee  = 0
            renewal_date = None

        # ── Unread notifications ──────────────────────────────────────
        unread_count = Notification.objects.filter(
            user    = user,
            is_read = False
        ).count()

        # ── Adverts — THIS operator's submissions ─────────────────────
        my_adverts_pending  = Advert.objects.filter(
            operator = user,
            status   = 'pending'
        ).count()
        my_adverts_approved = Advert.objects.filter(
            operator = user,
            status   = 'approved'
        ).count()

        # ── Disputes — THIS operator's raised disputes ─────────────────
        my_disputes_open = Dispute.objects.filter(
            operator   = user,
            status__in = ['open', 'under_review', 'investigating']
        ).count()
        my_disputes_resolved = Dispute.objects.filter(
            operator = user,
            status   = 'resolved'
        ).count()

        # ── Recent bills ──────────────────────────────────────────────
        recent_bills = Bill.objects.filter(
            operator=user
        ).order_by('-created_at')[:5].values(
            'invoice_id', 'billing_period',
            'total', 'status', 'created_at'
        )

        # ── Shop details ──────────────────────────────────────────────
        shop_list = []
        for shop in shops:
            shop_list.append({
                'id':               str(shop.id),
                'shop_number':      shop.shop_number,
                'block':            shop.block,
                'trading_name':     shop.trading_name,
                'electricity_type': shop.electricity_type,
                'iscooa_position':  shop.iscooa_position,
            })

        return Response({
            'user': {
                'name':          user.full_name,
                'email':         user.email,
                'member_number': user.member_number,
                'role':          user.role,
            },
            'stats': {
                'shops_on_profile':          shop_count,
                'outstanding_bills_count':   outstanding_count,
                'outstanding_bills_naira':   outstanding_amount / 100,
                'wallet_balance_naira':      balance,
                'coolmfb_account':           coolmfb_account,
                'subscription_status':       sub_status,
                'subscription_month':        sub_month,
                'monthly_fee_naira':         monthly_fee,
                'renewal_date':              renewal_date,
                'unread_notifications':      unread_count,
                'my_adverts_pending':        my_adverts_pending,
                'my_adverts_approved':       my_adverts_approved,
                'my_disputes_open':          my_disputes_open,
                'my_disputes_resolved':      my_disputes_resolved,
            },
            'my_shops':     shop_list,
            'recent_bills': list(recent_bills),
        })


@extend_schema(tags=['Overview'])
class ExecOverviewView(APIView):
    """
    GET /api/v1/overview/exec/
    Association Executive home dashboard.
    ALL counts are strictly scoped to this exec's association.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'is':
            return Response(
                {'detail': 'This overview is for ISCOOA executives only.'},
                status=403
            )

        from kyc.models import KYCApplication
        from adverts.models import Advert
        from disputes.models import Dispute
        from bills.models import Bill
        from subscriptions.models import SubscriptionPayment
        from notifications.models import Notification
        from polls.models import Poll
        from expenses.models import Expense

        assoc = user.association

        # ── KYC — scoped to this association ──────────────────────────
        kyc_pending  = KYCApplication.objects.filter(
            operator__association = assoc,
            status                = 'submitted'
        ).count()

        kyc_approved = KYCApplication.objects.filter(
            operator__association = assoc,
            status                = 'approved'
        ).count()

        # ── Adverts — scoped to this association ───────────────────────
        advert_queue = Advert.objects.filter(
            operator__association = assoc,
            status                = 'pending'
        ).count()

        # ── Disputes — scoped to this association ──────────────────────
        open_disputes = Dispute.objects.filter(
            operator__association = assoc,
            status__in            = ['open', 'under_review', 'investigating']
        ).count()

        # ── Bills — scoped to this association ─────────────────────────
        unpaid_bills = Bill.objects.filter(
            operator__association = assoc,
            status                = 'unpaid'
        ).count()

        unverified_bills = Bill.objects.filter(
            operator__association = assoc,
            status                = 'paid'
        ).count()

        # ── Revenue this month — scoped to this association ────────────
        month_str   = timezone.now().strftime('%Y-%m')
        sub_revenue = SubscriptionPayment.objects.filter(
            operator__association = assoc,
            status                = 'paid',
            period                = month_str,
        ).aggregate(total=Sum('iscooa_cut'))['total'] or 0

        advert_revenue = Advert.objects.filter(
            operator__association = assoc,
            status                = 'approved',
        ).aggregate(total=Sum('iscooa_cut'))['total'] or 0

        # ── Polls — scoped to this association ─────────────────────────
        active_polls = Poll.objects.filter(
            association = assoc,
            status      = 'active'
        ).count()

        # ── Pending expenses for THIS exec's role ─────────────────────
        pending_expenses = 0
        if user.ipos == 'treasurer':
            pending_expenses = Expense.objects.filter(
                association = assoc,
                status      = 'pending_treasurer'
            ).count()
        elif user.ipos == 'secretary_general':
            pending_expenses = Expense.objects.filter(
                association = assoc,
                status      = 'pending_secretary'
            ).count()
        elif user.ipos == 'president':
            pending_expenses = Expense.objects.filter(
                association = assoc,
                status      = 'pending_president'
            ).count()

        # ── Unread notifications for this exec ────────────────────────
        unread_count = Notification.objects.filter(
            user    = user,
            is_read = False
        ).count()

        return Response({
            'user': {
                'name':  user.full_name,
                'email': user.email,
                'role':  user.role,
                'ipos':  user.ipos,
            },
            'stats': {
                'kyc_pending':          kyc_pending,
                'kyc_approved':         kyc_approved,
                'advert_queue':         advert_queue,
                'open_disputes':        open_disputes,
                'unpaid_bills':         unpaid_bills,
                'unverified_bills':     unverified_bills,
                'active_polls':         active_polls,
                'pending_expenses':     pending_expenses,
                'unread_notifications': unread_count,
            },
            'revenue_mtd': {
                'subscription_commission_naira': sub_revenue / 100,
                'advert_commission_naira':       advert_revenue / 100,
                'total_naira':                   (sub_revenue + advert_revenue) / 100,
                'period':                        month_str,
            },
            'action_queue': {
                'kyc_applications_to_review': kyc_pending,
                'adverts_to_approve':         advert_queue,
                'bills_to_verify':            unverified_bills,
                'expenses_awaiting_you':      pending_expenses,
            },
        })


@extend_schema(tags=['Overview'])
class BOTOverviewView(APIView):
    """
    GET /api/v1/overview/bot/
    Board of Trustees home dashboard.
    All counts scoped to this BOT member's association.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'bot':
            return Response(
                {'detail': 'This overview is for BOT members only.'},
                status=403
            )

        from resolutions.models import Resolution, ResolutionVote
        from expenses.models import Expense
        from accounts.models import User

        assoc = user.association

        # ── Resolutions — scoped to this association ───────────────────
        pending_resolutions = Resolution.objects.filter(
            association = assoc,
            status      = 'pending'
        ).count()

        passed_ytd = Resolution.objects.filter(
            association         = assoc,
            status              = 'passed',
            ratified_date__year = timezone.now().year,
        ).count()

        # ── Expenses for BOT ratification — scoped to this association ─
        pending_ratification = Expense.objects.filter(
            association = assoc,
            status      = 'pending_bot'
        ).count()

        # ── BOT members in this association ────────────────────────────
        bot_members = User.objects.filter(
            role        = 'bot',
            association = assoc,
            is_active   = True
        ).count()

        # ── Resolutions THIS BOT member has not voted on yet ──────────
        pending_my_votes = Resolution.objects.filter(
            association = assoc,
            status      = 'pending'
        ).exclude(
            votes__bot_member = user
        ).count()

        return Response({
            'user': {
                'name':  user.full_name,
                'email': user.email,
                'role':  user.role,
            },
            'stats': {
                'resolutions_pending':       pending_resolutions,
                'expenses_for_ratification': pending_ratification,
                'resolutions_passed_ytd':    passed_ytd,
                'total_bot_members':         bot_members,
                'my_pending_votes':          pending_my_votes,
            },
            'action_queue': {
                'resolutions_to_vote_on': pending_my_votes,
                'expenses_to_ratify':     pending_ratification,
            },
        })


@extend_schema(tags=['Overview'])
class AdvisorOverviewView(APIView):
    """
    GET /api/v1/overview/advisor/
    Advisor home dashboard.
    All counts scoped to this advisor's association.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'adv':
            return Response(
                {'detail': 'This overview is for advisors only.'},
                status=403
            )

        from resolutions.models import Resolution, AdvisoryNote

        assoc = user.association

        # ── Resolutions awaiting this advisor's note ───────────────────
        resolutions_for_review = Resolution.objects.filter(
            association = assoc,
            status__in  = ['pending', 'draft']
        ).exclude(
            advisory_notes__advisor = user
        ).count()

        # ── This advisor's submitted notes ─────────────────────────────
        my_notes_count = AdvisoryNote.objects.filter(
            advisor = user
        ).count()

        # ── Total passed resolutions in this association ───────────────
        passed_count = Resolution.objects.filter(
            association = assoc,
            status      = 'passed'
        ).count()

        return Response({
            'user': {
                'name':  user.full_name,
                'email': user.email,
                'role':  user.role,
            },
            'stats': {
                'resolutions_for_review': resolutions_for_review,
                'my_notes_submitted':     my_notes_count,
                'resolutions_passed':     passed_count,
            },
            'action_queue': {
                'resolutions_awaiting_your_note': resolutions_for_review,
            },
            'banner': (
                'Advisory Role — Counsel Only. You can view resolutions, '
                'add advisory notes, and access financial summaries. '
                'You do not have approval or decision powers.'
            ),
        })


@extend_schema(tags=['Overview'])
class SuperAdminOverviewView(APIView):
    """
    GET /api/v1/overview/superadmin/
    Iprolance Super Admin platform overview.
    Shows platform-wide stats across all associations.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'sa':
            return Response(
                {'detail': 'This overview is for Super Admin only.'},
                status=403
            )

        from accounts.models import User
        from kyc.models import KYCApplication
        from subscriptions.models import SubscriptionPayment
        from adverts.models import Advert
        from audit.models import AuditLog

        # ── Platform-wide user counts ──────────────────────────────────
        total_users     = User.objects.filter(is_active=True).count()
        total_operators = User.objects.filter(role='op', is_active=True).count()
        total_exco      = User.objects.filter(role='is', is_active=True).count()
        total_bot       = User.objects.filter(role='bot', is_active=True).count()
        approved_members = KYCApplication.objects.filter(
            status='approved'
        ).count()

        # ── Iprolance revenue — 80% of subscription payments ──────────
        sub_iprolance = SubscriptionPayment.objects.filter(
            status='paid'
        ).aggregate(total=Sum('iprolance_cut'))['total'] or 0

        # ── Iprolance revenue — 80% of advert fees ────────────────────
        advert_iprolance = Advert.objects.filter(
            status='approved'
        ).aggregate(total=Sum('iprolance_cut'))['total'] or 0

        total_iprolance = sub_iprolance + advert_iprolance

        # ── Per-association breakdown ──────────────────────────────────
        associations_data = []
        for assoc in Association.objects.filter(is_active=True):
            assoc_operators = User.objects.filter(
                role        = 'op',
                association = assoc,
                is_active   = True
            ).count()

            assoc_approved = KYCApplication.objects.filter(
                operator__association = assoc,
                status                = 'approved'
            ).count()

            assoc_sub_revenue = SubscriptionPayment.objects.filter(
                operator__association = assoc,
                status                = 'paid'
            ).aggregate(total=Sum('iscooa_cut'))['total'] or 0

            associations_data.append({
                'id':                     str(assoc.id),
                'name':                   assoc.name,
                'slug':                   assoc.slug,
                'location':               assoc.location,
                'status':                 'active' if assoc.is_active else 'inactive',
                'total_operators':        assoc_operators,
                'approved_members':       assoc_approved,
                'association_revenue_naira': assoc_sub_revenue / 100,
            })

        # ── Recent audit entries ───────────────────────────────────────
        recent_audit = AuditLog.objects.all().order_by(
            '-timestamp'
        )[:5].values(
            'user_email', 'action',
            'table_name', 'record_ref', 'timestamp'
        )

        return Response({
            'user': {
                'name':  user.full_name,
                'email': user.email,
                'role':  user.role,
            },
            'platform_stats': {
                'total_active_users':  total_users,
                'total_operators':     total_operators,
                'total_exco_members':  total_exco,
                'total_bot_members':   total_bot,
                'approved_members':    approved_members,
                'total_associations':  Association.objects.filter(is_active=True).count(),
            },
            'iprolance_revenue': {
                'subscription_share_naira': sub_iprolance / 100,
                'advert_share_naira':       advert_iprolance / 100,
                'total_revenue_naira':      total_iprolance / 100,
            },
            'associations': associations_data,
            'recent_activity': list(recent_audit),
        })