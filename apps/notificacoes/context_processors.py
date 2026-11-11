from django.conf import settings


def notificacoes(request):
    """Chave pública das notificações para o navegador (vazia = notificações desligadas)."""
    return {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}
