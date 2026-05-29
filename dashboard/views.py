import json
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth
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

        from clients.models import Client
        from insurance.models import Policy, Proposal, Renewal
        from claims.models import Claim
        from commissions.models import Commission
        from crm.models import Deal, Stage, Pipeline

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

        ctx['total_commission_pending'] = Commission.objects.filter(
            brokerage=brokerage, status='pending'
        ).aggregate(total=Sum('insurer_amount'))['total'] or 0

        pipeline = Pipeline.objects.filter(brokerage=brokerage, is_default=True).first()
        if not pipeline:
            pipeline = Pipeline.objects.filter(brokerage=brokerage).first()

        funnel_labels = []
        funnel_values = []
        funnel_amounts = []
        funnel_colors = []

        if pipeline:
            stages = Stage.objects.filter(pipeline=pipeline).order_by('order')
            funnel_data = []
            max_count = 0
            for stage in stages:
                count = Deal.objects.filter(brokerage=brokerage, stage=stage).count()
                value = Deal.objects.filter(brokerage=brokerage, stage=stage).aggregate(
                    total=Sum('estimated_value')
                )['total'] or 0
                if count > max_count:
                    max_count = count
                funnel_data.append({
                    'name': stage.name,
                    'color': stage.color,
                    'is_won': stage.is_won,
                    'is_lost': stage.is_lost,
                    'count': count,
                    'value': value,
                    'pct': 0,
                })
                funnel_labels.append(stage.name)
                funnel_values.append(count)
                funnel_amounts.append(float(value))
                funnel_colors.append(stage.color)

            for idx, item in enumerate(funnel_data):
                item['pct'] = int((item['count'] / max_count) * 100) if max_count > 0 else 0
            ctx['funnel_data'] = funnel_data
        else:
            ctx['funnel_data'] = []

        ctx['funnel_labels'] = json.dumps(funnel_labels)
        ctx['funnel_values'] = json.dumps(funnel_values)
        ctx['funnel_amounts'] = json.dumps(funnel_amounts)
        ctx['funnel_colors'] = json.dumps(funnel_colors)

        policies_by_lob = list(Policy.objects.filter(
            brokerage=brokerage, status='active'
        ).values('line_of_business__name').annotate(
            count=Count('id'), total_premium=Sum('total_premium')
        ).order_by('-count'))

        ctx['policies_by_lob'] = policies_by_lob
        ctx['chart_lob_labels'] = json.dumps([item['line_of_business__name'] or 'Sem ramo' for item in policies_by_lob])
        ctx['chart_lob_values'] = json.dumps([item['count'] for item in policies_by_lob])

        claims_by_status = list(Claim.objects.filter(
            brokerage=brokerage
        ).values('status').annotate(count=Count('id'), total=Sum('claimed_amount')).order_by('-count'))

        status_display = {
            'opened': 'Aberto', 'under_analysis': 'Em Análise',
            'approved': 'Aprovado', 'paid': 'Pago', 'closed': 'Fechado',
        }
        ctx['claims_by_status'] = claims_by_status
        ctx['chart_claims_labels'] = json.dumps([status_display.get(item['status'], item['status']) for item in claims_by_status])
        ctx['chart_claims_values'] = json.dumps([item['count'] for item in claims_by_status])

        top_insurers = list(Policy.objects.filter(
            brokerage=brokerage, status='active'
        ).values('insurer__name').annotate(
            count=Count('id'), total_premium=Sum('total_premium')
        ).order_by('-total_premium')[:5])

        ctx['top_insurers'] = top_insurers
        ctx['chart_insurer_labels'] = json.dumps([item['insurer__name'] or 'N/A' for item in top_insurers])
        ctx['chart_insurer_values'] = json.dumps([item['count'] for item in top_insurers])

        monthly_premium = list(Policy.objects.filter(
            brokerage=brokerage, created_at__date__gte=period_start,
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            total=Sum('total_premium')
        ).order_by('month'))

        monthly_commission = list(Commission.objects.filter(
            brokerage=brokerage, created_at__date__gte=period_start,
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            total=Sum('insurer_amount')
        ).order_by('month'))

        month_labels = []
        premium_data = []
        commission_data = []
        for entry in monthly_premium:
            month_labels.append(entry['month'].strftime('%b/%Y') if entry['month'] else '')
            premium_data.append(float(entry['total'] or 0))

        for entry in monthly_commission:
            month_labels_commission = entry['month'].strftime('%b/%Y') if entry['month'] else ''
            commission_data.append(float(entry['total'] or 0))

        all_months = sorted(set(
            [e['month'].strftime('%b/%Y') for e in monthly_premium if e['month']] +
            [e['month'].strftime('%b/%Y') for e in monthly_commission if e['month']]
        ))

        premium_map = {e['month'].strftime('%b/%Y'): float(e['total'] or 0) for e in monthly_premium if e['month']}
        commission_map = {e['month'].strftime('%b/%Y'): float(e['total'] or 0) for e in monthly_commission if e['month']}

        ctx['chart_months'] = json.dumps(all_months)
        ctx['chart_premiums'] = json.dumps([premium_map.get(m, 0) for m in all_months])
        ctx['chart_commissions'] = json.dumps([commission_map.get(m, 0) for m in all_months])

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