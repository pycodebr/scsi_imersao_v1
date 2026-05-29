from django import forms
from django.forms import inlineformset_factory

from clients.models import Client
from insurers.models import Insurer, LineOfBusiness

from .models import CoveredItem, Proposal


class ProposalForm(forms.ModelForm):
    """Formulário de criação / edição de proposta.

    FK selects filtram ativos do tenant.
    """

    class Meta:
        model = Proposal
        fields = (
            'client', 'insurer', 'line_of_business', 'number',
            'status', 'net_premium', 'total_premium', 'iof',
            'proposed_start_date', 'proposed_end_date',
            'payment_terms', 'notes',
        )
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'insurer': forms.Select(attrs={'class': 'form-control'}),
            'line_of_business': forms.Select(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'net_premium': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_premium': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iof': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'proposed_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proposed_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if self.tenant:
            active_clients = Client.objects.filter(brokerage=self.tenant, is_active=True)
            active_insurers = Insurer.objects.filter(brokerage=self.tenant, is_active=True)
            active_lobs = LineOfBusiness.objects.filter(brokerage=self.tenant, is_active=True)
            self.fields['client'].queryset = active_clients
            self.fields['insurer'].queryset = active_insurers
            self.fields['line_of_business'].queryset = active_lobs


class CoveredItemForm(forms.ModelForm):
    class Meta:
        model = CoveredItem
        fields = ('item_type', 'description', 'identifier', 'insured_amount', 'attributes', 'coverages')
        widgets = {
            'item_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
            'insured_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'attributes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'coverages': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ProposalSearchForm(forms.Form):
    q = forms.CharField(label='Buscar', required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Número, cliente...',
    }))
    status = forms.ChoiceField(label='Status', required=False, choices=[('', 'Todos')] + Proposal.Status.choices,
                               widget=forms.Select(attrs={'class': 'form-control'}))
    insurer = forms.IntegerField(label='Seguradora', required=False, widget=forms.HiddenInput)
    line_of_business = forms.IntegerField(label='Ramo', required=False, widget=forms.HiddenInput)


CoveredItemInlineFormSet = inlineformset_factory(
    Proposal,
    CoveredItem,
    form=CoveredItemForm,
    extra=1,
    can_delete=True,
    fields=('item_type', 'description', 'identifier', 'insured_amount', 'attributes', 'coverages'),
)