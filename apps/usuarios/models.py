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

    # Cifreiro: cuida das músicas (cadastrar, editar, importar, acordes e relatório). Não exclui
    # músicas e não mexe em escalas, cultos nem integrantes. O líder já pode tudo isso.
    is_cifreiro = models.BooleanField(
        default=False
    )

    # Cadastro feito pelo próprio integrante fica pendente (não aprovado e inativo) até um líder aprovar.
    # Depois de aprovado, "is_active" é a chave de ativo/inativo da tela de Integrantes.
    aprovado = models.BooleanField(
        default=True
    )

    @property
    def pode_editar_musicas(self):
        return self.is_lider or self.is_cifreiro

    def __str__(self):
        return self.get_full_name() or self.username