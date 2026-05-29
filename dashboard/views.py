from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date, timedelta

from django.views.generic import TemplateView

from base.mixins import RoleRequiredMixin


class DashboardView(RoleRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        brokerage = self.request.tenant
        today = date.today()
        period_start = self._get_period_start()
        period_days = (today - period_start).days or 1

        from clients.models import Client
        from insurance.models import Policy, Proposal, Renewal
        from claims.models import Claim
        from commissions.models import Commission, CommissionSplit
        from crm.models import Deal, Stage, Pipeline
        from insurers.models import Insurer
        from partners.models import Agent, Producer

        ctx['total_clients'] = Client.objects.filter(brokerage=brokerage, is_active=True).count()
        ctx['active_policies'] = Policy.objects.filter(brokerage=brokerage, status='active').count()
        ctx['open_proposals'] = Proposal.objects.filter(
            brokerage=brokerage, status__in=('draft', 'sent', 'under_analysis')
        ).count()
        ctx['open_claims'] = Claim.objects.filter(
            brokerage=brokerage, status__in=('opened', 'under_analysis')
        ).count()

        renewals_due = Renewal.objects.filter(
            brokerage=brokerage,
            status='pending',
            due_date__lte=today + timedelta(days=30),
        ).count()
        ctx['renewals_due_30d'] = renewals_due

        ctx['total_commission_received'] = Commission.objects.filter(
            brokerage=brokerage, status='received'
        ).aggregate(total=Sum('insurer_amount'))['total'] or 0

        ctx['total_commission_pending'] = Commission.objects.filter(
            brokerage=brokerage, status='pending'
        ).aggregate(total=Sum('insurer_amount'))['total'] or 0

        pipeline = Pipeline.objects.filter(brokerage=brokerage, is_default=True).first()
        if not pipeline:
            pipeline = Pipeline.objects.filter(brokerage=brokerage).first()
        if pipeline:
            stages = Stage.objects.filter(pipeline=pipeline).order_by('order')
            funnel_data = []
            max_count = 0
            for stage in stages:
                count = Deal.objects.filter(
                    brokerage=brokerage, stage=stage
                ).count()
                if count > max_count:
                    max_count = count
                funnel_data.append({
                    'name': stage.name,
                    'color': stage.color,
                    'is_won': stage.is_won,
                    'is_lost': stage.is_lost,
                    'count': count,
                    'value': 0,
                    'pct': 0,
                })
            for idx, stage in enumerate(stages):
                value = Deal.objects.filter(
                    brokerage=brokerage, stage=stage
                ).aggregate(total=Sum('estimated_value'))['total'] or 0
                funnel_data[idx]['value'] = value
                funnel_data[idx]['pct'] = int((funnel_data[idx]['count'] / max_count) * 100) if max_count > 0 else 0
            ctx['funnel_data'] = funnel_data
        else:
            ctx['funnel_data'] = []

        policies_by_lob = Policy.objects.filter(
            brokerage=brokerage, status='active'
        ).values('line_of_business__name').annotate(
            count=Count('id'), total_premium=Sum('total_premium')
        ).order_by('-count')
        ctx['policies_by_lob'] = list(policies_by_lob)

        monthly_premium = Policy.objects.filter(
            brokerage=brokerage,
            created_at__date__gte=period_start,
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            total=Sum('total_premium')
        ).order_by('month')
        ctx['monthly_premium'] = list(monthly_premium)

        monthly_commission = Commission.objects.filter(
            brokerage=brokerage,
            created_at__date__gte=period_start,
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            total=Sum('insurer_amount')
        ).order_by('month')
        ctx['monthly_commission'] = list(monthly_commission)

        claims_by_status = Claim.objects.filter(
            brokerage=brokerage
        ).values('status').annotate(count=Count('id'), total=Sum('claimed_amount')).order_by('-count')
        ctx['claims_by_status'] = list(claims_by_status)

        top_insurers = Policy.objects.filter(
            brokerage=brokerage, status='active'
        ).values('insurer__name').annotate(
            count=Count('id'), total_premium=Sum('total_premium')
        ).order_by('-total_premium')[:5]
        ctx['top_insurers'] = list(top_insurers)

        ctx['period_start'] = period_start
        ctx['period_end'] = today
        return ctx

    def _get_period_start(self):
        period = self.request.GET.get('period', '30')
        today = date.today()
        if period == '7':
            return today - timedelta(days=7)
        elif period == '90':
            return today - timedelta(days=90)
        elif period == '365':
            return today - timedelta(days=365)
        return today - timedelta(days=30)