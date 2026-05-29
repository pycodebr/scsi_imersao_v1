from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuário customizado do projeto.

    Definido já na Sprint 1 para fixar ``AUTH_USER_MODEL='accounts.User'`` antes
    do primeiro migrate (não é possível trocar o user model depois de migrar).
    O login por e-mail (``USERNAME_FIELD='email'``) e o ``EmailBackend`` são
    introduzidos na Sprint 4.
    """

    pass
