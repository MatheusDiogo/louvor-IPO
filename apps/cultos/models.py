from django.db import models


class TipoCulto(models.Model):

    DIAS_SEMANA = [
        (0, "Segunda"),
        (1, "Terça"),
        (2, "Quarta"),
        (3, "Quinta"),
        (4, "Sexta"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    nome = models.CharField(
        max_length=100
    )

    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA
    )

    horario = models.TimeField()

    ativo = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.nome} - {self.get_dia_semana_display()} {self.horario}"
    
from django.conf import settings

class Culto(models.Model):

    tipo = models.ForeignKey(
        TipoCulto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cultos"
    )

    data = models.DateTimeField()

    def __str__(self):
        return f"Culto {self.data.strftime('%d/%m/%Y %H:%M')}"