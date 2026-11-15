"""Copia uma vez os dados do SQLite antigo (volume do Railway) para o Postgres.

Roda no início de cada deploy (Dockerfile), logo depois do `migrate`. Só faz alguma coisa quando:
  - o banco principal é Postgres (variável DATABASE_URL);
  - o arquivo SQLite antigo existe (alias "sqlite_antigo" em settings.py);
  - o Postgres ainda não tem nenhum integrante (ou seja, a cópia ainda não foi feita).
O arquivo SQLite não é apagado: fica como cópia de segurança.
"""
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections, transaction

# Fora da cópia: o Django recria sozinho (tipos de conteúdo, permissões) ou não interessa (sessões, log do admin)
EXCLUIR = ['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session']


class Command(BaseCommand):
    help = 'Copia os dados do SQLite antigo para o Postgres (uma vez só; seguro rodar em todo deploy).'

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            self.stdout.write('Banco principal não é Postgres: nada a copiar.')
            return
        if 'sqlite_antigo' not in connections.databases:
            self.stdout.write('Nenhum SQLite antigo encontrado: nada a copiar.')
            return
        Usuario = get_user_model()
        if Usuario.objects.exists():
            self.stdout.write('O Postgres já tem dados: cópia já feita antes.')
            return

        # O SQLite pode estar numa versão anterior do sistema: atualiza as tabelas dele antes de copiar
        self.stdout.write('Atualizando o SQLite antigo...')
        call_command('migrate', database='sqlite_antigo', interactive=False, verbosity=0)
        if not Usuario.objects.using('sqlite_antigo').exists():
            self.stdout.write('O SQLite antigo está vazio: nada a copiar.')
            return

        arquivo = os.path.join(tempfile.gettempdir(), 'louvor_dados_sqlite.json')
        self.stdout.write('Exportando os dados do SQLite...')
        with open(arquivo, 'w', encoding='utf-8') as saida:  # UTF-8 sempre (acentos), em qualquer sistema
            call_command('dumpdata', database='sqlite_antigo', natural_foreign=True, exclude=EXCLUIR,
                         stdout=saida, verbosity=0)

        self.stdout.write('Importando no Postgres...')
        from apps.musicas.models import DesenhoAcorde, NomeAcorde
        from apps.notificacoes.models import AvisoProgramado
        try:
            with transaction.atomic():
                # As migrações já preencheram a base de acordes, as grafias padrão e os avisos da
                # disponibilidade no Postgres; apaga para entrarem exatamente os do SQLite
                DesenhoAcorde.objects.all().delete()
                NomeAcorde.objects.all().delete()
                AvisoProgramado.objects.all().delete()
                call_command('loaddata', arquivo, verbosity=0)
        except Exception as erro:
            raise CommandError(f'Falha ao importar no Postgres (nada foi gravado): {erro}') from erro
        finally:
            if os.path.exists(arquivo):
                os.remove(arquivo)

        self.stdout.write(self.style.SUCCESS(
            f'Dados copiados para o Postgres: {Usuario.objects.count()} integrante(s). '
            'O SQLite antigo continua no volume como cópia de segurança.'))
