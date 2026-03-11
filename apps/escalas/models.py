from django.db import models
from apps.musicas.models import Musica, Tom
from django.core.exceptions import ValidationError

class Escala(models.Model):
    data = models.DateField(
        unique=True
    )
    observacao = models.TextField(blank=True, null=True)
        
    def __str__(self):
        return f"Escala de {self.data}"

# Modelo intermediário para vincular músicas + tons à escala
class EscalaMusica(models.Model):
    escala = models.ForeignKey(
        Escala,
        on_delete=models.CASCADE,
        related_name="itens"
    )

    musica = models.ForeignKey(
        Musica,
        on_delete=models.CASCADE
    )

    tom = models.ForeignKey(
        Tom,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('escala', 'musica')

    def __str__(self):
        return f"{self.musica.nome} ({self.tom.tom}) na escala de {self.escala.data}"