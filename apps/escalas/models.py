from django.db import models
from apps.musicas.models import Musica, Tom

class Escala(models.Model):
    data = models.DateField(blank=False, null=False)
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Escala de {self.data}"

# Modelo intermediário para vincular músicas + tons à escala
class EscalaMusica(models.Model):
    escala = models.ForeignKey(Escala, on_delete=models.CASCADE, related_name="musicas")
    musica = models.ForeignKey(Musica, on_delete=models.CASCADE)
    tom = models.ForeignKey(Tom, on_delete=models.CASCADE)
    observacao = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('escala', 'musica', 'tom')  # evita duplicatas exatas

    def __str__(self):
        return f"{self.musica.nome} ({self.tom.tom}) na escala de {self.escala.data}"