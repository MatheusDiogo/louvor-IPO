import json
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class AppsScriptEmailBackend(BaseEmailBackend):
    """Envia e-mails via Google Apps Script (HTTPS), já que o Railway bloqueia SMTP."""

    def send_messages(self, email_messages):
        enviados = 0
        for message in email_messages:
            try:
                self._enviar(message)
                enviados += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return enviados

    def _enviar(self, message):
        html = next(
            (conteudo for conteudo, tipo in getattr(message, 'alternatives', []) if tipo == 'text/html'),
            None,
        )
        payload = {
            'secret': settings.APPS_SCRIPT_EMAIL_SECRET,
            'to': ','.join(message.recipients()),
            'subject': message.subject,
            'body': message.body,
            'htmlBody': html,
        }
        req = urllib.request.Request(
            settings.APPS_SCRIPT_EMAIL_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=settings.EMAIL_TIMEOUT) as resp:
            resposta = json.loads(resp.read().decode('utf-8'))
        if not resposta.get('ok'):
            raise RuntimeError(f"Apps Script recusou o envio: {resposta.get('error')}")
