from django.conf import settings
from django.db import models
from apps.instrumentos.models import Instrumento
from apps.musicas.models import Musica, Tom

class Escala(models.Model):
    data = models.DateField(
        unique=True
    )
    observacao = models.TextField(blank=True, null=True)

    # Integrante responsável pela ministração no culto (marcado com * na escala)
    ministrante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cultos_ministrados"
    )

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


# Integrante escalado em um instrumento no culto
class EscalaIntegrante(models.Model):
    escala = models.ForeignKey(
        Escala,
        on_delete=models.CASCADE,
        related_name="integrantes"
    )

    instrumento = models.ForeignKey(
        Instrumento,
        on_delete=models.CASCADE,
        related_name="escalacoes"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="escalacoes"
    )

    class Meta:
        unique_together = ('escala', 'instrumento', 'usuario')

    def __str__(self):
        return f"{self.usuario} ({self.instrumento}) em {self.escala.data}"
