"""Envia os avisos programados que estão na hora. Rodado pelo serviço "cron" do Railway de hora em hora:

    python manage.py enviar_avisos

Pode rodar mais de uma vez na mesma hora sem repetir avisos.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notificacoes import programados


class Command(BaseCommand):
    help = 'Envia os avisos programados que estão na hora (cadastrados na tela Avisos programados).'

    def handle(self, *args, **options):
        agora = timezone.localtime()
        feitos = programados.rodar(agora)
        if not feitos:
            self.stdout.write(f'{agora:%d/%m/%Y %H:%M}: nenhum aviso nesta hora.')
        for envio in feitos:
            texto = (f'{agora:%d/%m/%Y %H:%M}: "{envio.aviso}" -> {envio.pessoas} pessoa(s), '
                     f'{envio.celulares} notificação(ões)')
            self.stdout.write(self.style.ERROR(texto + f' ERRO: {envio.erro}') if envio.erro else self.style.SUCCESS(texto))
