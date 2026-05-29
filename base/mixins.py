from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

from base.managers import current_tenant


class TenantQuerysetMixin:
    """Filtra automaticamente o queryset da view pelo tenant do usuário.

    A view que herdar este mixin define ``request.tenant`` (via
    ``TenantMiddleware``) e o ``get_queryset`` aplica
    ``Model.objects.for_tenant(request.tenant)``.

    Se o usuário não tiver ``brokerage``, retorna queryset vazio (nenhum dado
    é visível sem tenant).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None) or current_tenant.get()
        if tenant is None:
            return qs.none()
        return qs.for_tenant(tenant)


class RoleRequiredMixin(AccessMixin):
    """Bloqueia o acesso se o usuário não tiver um dos ``allowed_roles``.

    ``allowed_roles`` pode ser uma lista/tupla de strings ou uma string única.
    O campo ``role`` do ``User`` é introduzido na Sprint 7; até lá, o mixin
    permite acesso a qualquer usuário autenticado com ``brokerage``.
    """

    allowed_roles = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            raise PermissionDenied('Usuário sem corretora vinculada.')

        # Sprint 7 introduzirá o campo `role`; aqui validamos só o vínculo.
        # Quando `role` existir, descomente o bloco abaixo:
        # if self.allowed_roles:
        #     if request.user.role not in (self.allowed_roles if isinstance(self.allowed_roles, (list, tuple)) else (self.allowed_roles,)):
        #         raise PermissionDenied('Papel não autorizado.')

        return super().dispatch(request, *args, **kwargs)