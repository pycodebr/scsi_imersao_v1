from django.urls import path

from .views import (
    GeneratePolicyFromProposalView,
    PolicyCreateView,
    PolicyDetailView,
    PolicyItemsJsonView,
    PolicyListView,
    PolicyUpdateView,
    ProposalCreateView,
    ProposalDetailView,
    ProposalListView,
    ProposalUpdateView,
)

app_name = 'insurance'

urlpatterns = [
    path('propostas/', ProposalListView.as_view(), name='proposal_list'),
    path('propostas/create/', ProposalCreateView.as_view(), name='proposal_create'),
    path('propostas/<int:pk>/', ProposalDetailView.as_view(), name='proposal_detail'),
    path('propostas/<int:pk>/edit/', ProposalUpdateView.as_view(), name='proposal_update'),
    path('propostas/<int:pk>/generate-policy/', GeneratePolicyFromProposalView.as_view(), name='proposal_generate_policy'),
    path('apolices/', PolicyListView.as_view(), name='policy_list'),
    path('apolices/create/', PolicyCreateView.as_view(), name='policy_create'),
    path('apolices/<int:pk>/', PolicyDetailView.as_view(), name='policy_detail'),
    path('apolices/<int:pk>/edit/', PolicyUpdateView.as_view(), name='policy_update'),
    path('apolices/<int:pk>/items-json/', PolicyItemsJsonView.as_view(), name='policy_items_json'),
]