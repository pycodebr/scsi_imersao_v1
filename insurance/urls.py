from django.urls import path

from .views import ProposalCreateView, ProposalDetailView, ProposalListView, ProposalUpdateView

app_name = 'insurance'

urlpatterns = [
    path('propostas/', ProposalListView.as_view(), name='proposal_list'),
    path('propostas/create/', ProposalCreateView.as_view(), name='proposal_create'),
    path('propostas/<int:pk>/', ProposalDetailView.as_view(), name='proposal_detail'),
    path('propostas/<int:pk>/edit/', ProposalUpdateView.as_view(), name='proposal_update'),
]