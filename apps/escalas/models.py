from django.db import models
from apps.cultos.models import Culto
from apps.usuarios.models import Usuario
from apps.instrumentos.models import Instrumento


class Escala(models.Model):

    culto = models.ForeignKey(
        Culto,
        on_delete=models.CASCADE,
        related_name="escalas"
    )

    musico = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.CASCADE
    )

    responsavel = models.BooleanField(
        default=False
    )

    observacao = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.culto} - {self.instrumento} - {self.musico}"