from django.conf import settings
from django.db import models


class InscricaoPush(models.Model):
    """Um celular/navegador que aceitou receber notificações (endereço de entrega do Web Push)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscricoes_push',
    )
    endpoint = models.CharField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    navegador = models.CharField(max_length=300, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.usuario} ({self.navegador[:40]})'

