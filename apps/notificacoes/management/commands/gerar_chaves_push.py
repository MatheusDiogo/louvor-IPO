import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b'=').decode()


class Command(BaseCommand):
    help = 'Gera o par de chaves VAPID para as notificações push (coloque nas variáveis do Railway).'

    def handle(self, *args, **opcoes):
        privada = ec.generate_private_key(ec.SECP256R1())
        bytes_privada = privada.private_numbers().private_value.to_bytes(32, 'big')
        bytes_publica = privada.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.stdout.write('Adicione estas variáveis no Railway (Variables):\n')
        self.stdout.write(f'VAPID_PUBLIC_KEY={_b64(bytes_publica)}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={_b64(bytes_privada)}')
        self.stdout.write('VAPID_EMAIL=seu-email@exemplo.com')
        self.stdout.write('\nGuarde a chave privada com segurança. Se trocar as chaves, todos precisam reativar as notificações.')
