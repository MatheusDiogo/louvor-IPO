from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.instrumentos.models import Instrumento

class Usuario(AbstractUser):

    instrumentos = models.ManyToManyField(
        Instrumento,
        blank=True,
        related_name="musicos"
    )

    email = models.EmailField(
        unique=True
    )

    is_lider = models.BooleanField(
        default=False
    )

    # Cadastro feito pelo próprio integrante fica pendente (não aprovado e inativo) até um líder aprovar.
    # Depois de aprovado, "is_active" é a chave de ativo/inativo da tela de Integrantes.
    aprovado = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.get_full_name() or self.username