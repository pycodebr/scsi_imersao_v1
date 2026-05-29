from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from base.mixins import RoleRequiredMixin, TenantQuerysetMixin
from documents.models import Document
from .forms import (
    CoveredItemInlineFormSet,
    GeneratePolicyForm,
    PolicyForm,
    PolicySearchForm,
    ProposalForm,
    ProposalSearchForm,
)
from .models import Policy, Proposal
from .services import generate_policy_from_proposal


class ProposalListView(RoleRequiredMixin, TenantQuerysetMixin, ListView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Proposal
    template_name = 'insurance/proposal_list.html'
    context_object_name = 'proposals'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('client', 'insurer', 'line_of_business')
        form = ProposalSearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get('q')
            status = form.cleaned_data.get('status')
            if q:
                qs = qs.filter(Q(number__icontains=q) | Q(client__name__icontains=q))
            if status:
                qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = ProposalSearchForm(self.request.GET)
        ctx['status_choices'] = Proposal.Status.choices
        return ctx


class ProposalCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer')
    model = Proposal
    form_class = ProposalForm
    template_name = 'insurance/proposal_form.html'
    success_url = reverse_lazy('insurance:proposal_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = CoveredItemInlineFormSet(self.request.POST)
        else:
            ctx['formset'] = CoveredItemInlineFormSet()
        return ctx

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f'Proposta "{self.object.number}" criada com sucesso.')
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class ProposalUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent')
    model = Proposal
    form_class = ProposalForm
    template_name = 'insurance/proposal_form.html'
    success_url = reverse_lazy('insurance:proposal_list')

    def get_queryset(self):
        return Proposal.objects.filter(brokerage=self.request.tenant)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = CoveredItemInlineFormSet(self.request.POST, instance=self.object)
        else:
            ctx['formset'] = CoveredItemInlineFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f'Proposta "{self.object.number}" atualizada.')
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class ProposalDetailView(RoleRequiredMixin, TenantQuerysetMixin, DetailView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Proposal
    template_name = 'insurance/proposal_detail.html'
    context_object_name = 'proposal'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        proposal = self.object
        proposal_ct = ContentType.objects.get_for_model(Proposal)
        ctx['content_type_id'] = proposal_ct.pk
        ctx['documents'] = Document.objects.filter(
            content_type=proposal_ct,
            object_id=proposal.pk,
            brokerage=self.request.tenant,
        ).order_by('-created_at')
        ctx['active_tab'] = self.request.GET.get('tab', 'info')
        ctx['can_generate_policy'] = proposal.status != Proposal.Status.CONVERTED
        return ctx


class GeneratePolicyFromProposalView(RoleRequiredMixin, View):
    """Gera apólice a partir da proposta — via POST no detail da proposal."""
    allowed_roles = ('owner', 'manager', 'broker')

    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk, brokerage=request.tenant)
        form = GeneratePolicyForm(request.POST)
        if form.is_valid():
            try:
                policy = generate_policy_from_proposal(proposal.pk, form.cleaned_data['policy_number'])
                messages.success(request, f'Apólice "{policy.policy_number}" gerada com sucesso.')
                return redirect('insurance:policy_detail', pk=policy.pk)
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Número da apólice inválido.')
        return redirect('insurance:proposal_detail', pk=pk)


# ── Apólices ──────────────────────────────────────────────────────────────────

class PolicyListView(RoleRequiredMixin, TenantQuerysetMixin, ListView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Policy
    template_name = 'insurance/policy_list.html'
    context_object_name = 'policies'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('client', 'insurer', 'line_of_business')
        form = PolicySearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get('q')
            status = form.cleaned_data.get('status')
            if q:
                qs = qs.filter(Q(policy_number__icontains=q) | Q(client__name__icontains=q))
            if status:
                qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = PolicySearchForm(self.request.GET)
        ctx['status_choices'] = Policy.Status.choices
        return ctx


class PolicyCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ('owner', 'manager', 'broker')
    model = Policy
    form_class = PolicyForm
    template_name = 'insurance/policy_form.html'
    success_url = reverse_lazy('insurance:policy_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        messages.success(self.request, f'Apólice "{form.instance.policy_number}" criada com sucesso.')
        return super().form_valid(form)


class PolicyUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = ('owner', 'manager', 'broker')
    model = Policy
    form_class = PolicyForm
    template_name = 'insurance/policy_form.html'
    success_url = reverse_lazy('insurance:policy_list')

    def get_queryset(self):
        return Policy.objects.filter(brokerage=self.request.tenant)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Apólice "{form.instance.policy_number}" atualizada.')
        return super().form_valid(form)


class PolicyDetailView(RoleRequiredMixin, TenantQuerysetMixin, DetailView):
    allowed_roles = ('owner', 'manager', 'broker', 'agent', 'producer', 'operational')
    model = Policy
    template_name = 'insurance/policy_detail.html'
    context_object_name = 'policy'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        policy = self.object
        policy_ct = ContentType.objects.get_for_model(Policy)
        ctx['content_type_id'] = policy_ct.pk
        ctx['documents'] = Document.objects.filter(
            content_type=policy_ct,
            object_id=policy.pk,
            brokerage=self.request.tenant,
        ).order_by('-created_at')
        ctx['active_tab'] = self.request.GET.get('tab', 'info')
        return ctx