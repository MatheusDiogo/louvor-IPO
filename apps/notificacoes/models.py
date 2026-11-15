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


class AvisoProgramado(models.Model):
    """Notificação enviada automaticamente, cadastrada na tela "Avisos programados" (só o administrador).

    Quando: uma expressão cron (minuto hora dia mês dia-da-semana), no horário de Recife.
    Para quem: uma consulta SQL (só SELECT) cuja coluna `id` são os integrantes; as outras colunas
    viram variáveis da mensagem ({instrumento}, {data_culto}...). A consulta também pode servir de
    condição: se não devolver ninguém naquela hora, nada é enviado.
    """

    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    cron = models.CharField(max_length=100, help_text='minuto hora dia mês dia-da-semana')
    titulo = models.CharField(max_length=120)
    mensagem = models.TextField()
    url = models.CharField(max_length=200, default='/home/', help_text='Página aberta ao tocar na notificação')
    consulta = models.TextField(help_text='SELECT que devolve a coluna id dos integrantes')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class EnvioAviso(models.Model):
    """Histórico: cada vez que um aviso saiu. A chave impede enviar duas vezes no mesmo período."""

    aviso = models.ForeignKey(AvisoProgramado, on_delete=models.SET_NULL, null=True, blank=True, related_name='envios')
    chave = models.CharField(max_length=100, unique=True)
    enviado_em = models.DateTimeField(auto_now_add=True)
    pessoas = models.PositiveIntegerField(default=0, help_text='Integrantes selecionados')
    celulares = models.PositiveIntegerField(default=0, help_text='Notificações entregues')
    teste = models.BooleanField(default=False)
    erro = models.TextField(blank=True)

    class Meta:
        ordering = ['-enviado_em']

    def __str__(self):
        return self.chave

