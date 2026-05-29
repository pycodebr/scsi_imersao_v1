import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View

from base.mixins import RoleRequiredMixin, TenantQuerysetMixin
from .models import Deal, DealStageHistory, Pipeline, Stage
from .forms import DealForm, PipelineForm, StageForm


class PipelineListView(RoleRequiredMixin, TenantQuerysetMixin, ListView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Pipeline
    template_name = 'crm/pipeline_list.html'
    context_object_name = 'pipelines'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('stages')


class PipelineCreateView(RoleRequiredMixin, TenantQuerysetMixin, CreateView):
    allowed_roles = ('owner', 'manager')
    model = Pipeline
    form_class = PipelineForm
    template_name = 'crm/pipeline_form.html'

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('crm:pipeline_list')


class PipelineUpdateView(RoleRequiredMixin, TenantQuerysetMixin, UpdateView):
    allowed_roles = ('owner', 'manager')
    model = Pipeline
    form_class = PipelineForm
    template_name = 'crm/pipeline_form.html'

    def get_success_url(self):
        return reverse_lazy('crm:pipeline_list')


class StageCreateView(RoleRequiredMixin, TenantQuerysetMixin, CreateView):
    allowed_roles = ('owner', 'manager')
    model = Stage
    form_class = StageForm
    template_name = 'crm/stage_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial']['pipeline'] = self.request.GET.get('pipeline')
        return kwargs

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('crm:pipeline_list')


class DealListView(RoleRequiredMixin, TenantQuerysetMixin, ListView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Deal
    template_name = 'crm/deal_list.html'
    context_object_name = 'deals'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('stage', 'client', 'pipeline')
        params = self.request.GET
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('pipeline_id'):
            qs = qs.filter(pipeline_id=params['pipeline_id'])
        return qs


class DealCreateView(RoleRequiredMixin, TenantQuerysetMixin, CreateView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer')
    model = Deal
    form_class = DealForm
    template_name = 'crm/deal_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('crm:deal_detail', kwargs={'pk': self.object.pk})


class DealUpdateView(RoleRequiredMixin, TenantQuerysetMixin, UpdateView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer')
    model = Deal
    form_class = DealForm
    template_name = 'crm/deal_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('crm:deal_detail', kwargs={'pk': self.object.pk})


class DealDetailView(RoleRequiredMixin, TenantQuerysetMixin, DetailView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Deal
    template_name = 'crm/deal_detail.html'
    context_object_name = 'deal'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'pipeline', 'stage', 'client', 'producer', 'agent',
            'insurer', 'line_of_business', 'proposal',
        ).prefetch_related(
            'stage_histories__from_stage',
            'stage_histories__to_stage',
            'stage_histories__changed_by',
        )


class DealKanbanView(RoleRequiredMixin, TenantQuerysetMixin, ListView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Deal
    template_name = 'crm/deal_kanban.html'
    context_object_name = 'deals'

    def get_queryset(self):
        return Deal.objects.filter(
            brokerage=self.request.tenant,
        ).select_related('stage', 'client', 'pipeline')


class DealMoveStageView(RoleRequiredMixin, View):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer')

    def post(self, request, pk):
        import json as _json
        data = _json.loads(request.body)
        deal = get_object_or_404(Deal, pk=pk, brokerage=request.tenant)
        new_stage_id = data.get('stage_id')
        new_stage = get_object_or_404(Stage, pk=new_stage_id, pipeline=deal.pipeline, brokerage=request.tenant)
        old_stage = deal.stage
        deal.stage = new_stage
        if new_stage.is_won:
            deal.status = Deal.Status.WON
        elif new_stage.is_lost:
            deal.status = Deal.Status.LOST
        else:
            deal.status = Deal.Status.OPEN
        deal.save(update_fields=['stage', 'status', 'updated_at'])
        DealStageHistory.objects.create(
            brokerage=request.tenant,
            deal=deal,
            from_stage=old_stage,
            to_stage=new_stage,
            changed_by=request.user,
        )
        return JsonResponse({'ok': True})


class DealKanbanJsonView(RoleRequiredMixin, View):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')

    def get(self, request):
        pipelines = Pipeline.objects.filter(brokerage=request.tenant)
        data = []
        for pipeline in pipelines:
            stages = Stage.objects.filter(pipeline=pipeline).order_by('order')
            stages_data = []
            for stage in stages:
                deals = Deal.objects.filter(
                    brokerage=request.tenant,
                    pipeline=pipeline,
                    stage=stage,
                ).select_related('client', 'producer')[:50]
                stages_data.append({
                    'id': stage.id,
                    'name': stage.name,
                    'color': stage.color,
                    'is_won': stage.is_won,
                    'is_lost': stage.is_lost,
                    'deals': [
                        {
                            'id': d.id,
                            'title': d.title,
                            'client': d.client.name if d.client else None,
                            'estimated_value': str(d.estimated_value),
                            'status': d.status,
                            'url': d.get_absolute_url(),
                        }
                        for d in deals
                    ],
                })
            data.append({
                'id': pipeline.id,
                'name': pipeline.name,
                'stages': stages_data,
            })
        return JsonResponse(data, safe=False)