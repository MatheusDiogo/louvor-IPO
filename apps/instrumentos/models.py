from django.db import models


class Instrumento(models.Model):

    nome = models.CharField(
        max_length=100,
        unique=True
    )

    ordem = models.PositiveIntegerField(
        default=0,
        help_text="Posição da coluna na escala de integrantes"
    )

    class Meta:
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome
