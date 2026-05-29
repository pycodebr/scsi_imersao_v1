from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from base.mixins import TenantQuerysetMixin
from .models import Claim
from .forms import ClaimForm, ClaimSearchForm


class ClaimListView(TenantQuerysetMixin, LoginRequiredMixin, ListView):
    model = Claim
    template_name = 'claims/claim_list.html'
    context_object_name = 'claims'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('policy', 'covered_item')
        params = self.request.GET
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('policy_id'):
            qs = qs.filter(policy_id=params['policy_id'])
        if params.get('date_from'):
            qs = qs.filter(occurrence_date__gte=params['date_from'])
        if params.get('date_to'):
            qs = qs.filter(occurrence_date__lte=params['date_to'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = ClaimSearchForm(self.request.GET or None)
        return ctx


class ClaimCreateView(TenantQuerysetMixin, LoginRequiredMixin, CreateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'claims/claim_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['brokerage'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.brokerage = self.request.tenant
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('claims:claim_detail', kwargs={'pk': self.object.pk})


class ClaimUpdateView(TenantQuerysetMixin, LoginRequiredMixin, UpdateView):
    model = Claim
    form_class = ClaimForm
    template_name = 'claims/claim_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['brokerage'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('claims:claim_detail', kwargs={'pk': self.object.pk})


class ClaimDetailView(TenantQuerysetMixin, LoginRequiredMixin, DetailView):
    model = Claim
    template_name = 'claims/claim_detail.html'
    context_object_name = 'claim'