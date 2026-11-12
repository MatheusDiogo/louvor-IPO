from django.core.management.base import BaseCommand

from apps.musicas.acordes import importar_base
from apps.musicas.models import DesenhoAcorde, NomeAcorde


class Command(BaseCommand):
    help = ('Recarrega os desenhos de acordes da base pública (chords-db). '
            'Os desenhos e nomes cadastrados pela equipe são mantidos.')

    def handle(self, *args, **options):
        total = importar_base(DesenhoAcorde, NomeAcorde)
        self.stdout.write(self.style.SUCCESS(f'{total} desenhos da base pública importados.'))
