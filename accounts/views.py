from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import EmailAuthenticationForm, UserProfileForm, UserRegistrationForm
from .models import User


class RegisterView(CreateView):
    """Cadastro de usuário; autentica e redireciona ao onboarding."""

    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('tenants:onboarding')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object, backend='accounts.backends.EmailBackend')
        messages.success(self.request, 'Conta criada com sucesso. Bem-vindo(a)!')
        return response


class EmailLoginView(LoginView):
    """Login por e-mail usando o template do Design System."""

    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class ProfileView(LoginRequiredMixin, UpdateView):
    """Edição do perfil do próprio usuário autenticado."""

    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado.')
        return super().form_valid(form)
