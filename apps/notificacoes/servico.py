"""Envio de notificações push (Web Push) para os celulares inscritos.

As chaves VAPID ficam nas variáveis de ambiente VAPID_PUBLIC_KEY e VAPID_PRIVATE_KEY
(gere com: python manage.py gerar_chaves_push). Sem elas, as notificações ficam desligadas.
"""
import json
import logging
import threading

from django.conf import settings
from django.db import close_old_connections, transaction

logger = logging.getLogger(__name__)


def configurado():
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _enviar_agora(usuario_ids, payload, ttl):
    from pywebpush import WebPushException, webpush
    from .models import InscricaoPush

    enviados = 0
    for inscricao in InscricaoPush.objects.filter(usuario_id__in=usuario_ids, usuario__is_active=True):
        try:
            webpush(
                subscription_info={'endpoint': inscricao.endpoint,
                                   'keys': {'p256dh': inscricao.p256dh, 'auth': inscricao.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': f'mailto:{settings.VAPID_EMAIL}'},
                ttl=ttl,
                timeout=10,
            )
            enviados += 1
        except WebPushException as erro:
            status = getattr(erro.response, 'status_code', None)
            if status in (404, 410):
                inscricao.delete()  # app desinstalado ou notificações bloqueadas: endereço não existe mais
            else:
                logger.warning('Falha ao enviar notificação (%s): %s', status, erro)
        except Exception:
            logger.exception('Erro inesperado ao enviar notificação')
    return enviados


def enviar(usuarios, titulo, corpo, url='/home/', tag=None, ttl=24 * 3600, em_segundo_plano=True):
    """Envia a mesma notificação para os usuários (objetos ou ids).

    `tag`: notificações com a mesma tag se substituem no celular (evita acumular avisos repetidos).
    Por padrão o envio acontece em segundo plano, depois que a transação do banco termina,
    para não deixar a pessoa esperando.
    """
    if not configurado():
        return 0
    ids = sorted({getattr(u, 'pk', u) for u in usuarios if u is not None})
    if not ids:
        return 0
    payload = json.dumps({'titulo': titulo, 'corpo': corpo, 'url': url, 'tag': tag or ''}, ensure_ascii=False)

    if not em_segundo_plano:
        return _enviar_agora(ids, payload, ttl)

    def tarefa():
        try:
            _enviar_agora(ids, payload, ttl)
        finally:
            close_old_connections()

    transaction.on_commit(lambda: threading.Thread(target=tarefa, daemon=True).start())
    return len(ids)


def enviar_personalizado(mensagens, url='/home/', tag=None, ttl=24 * 3600, em_segundo_plano=True):
    """`mensagens`: {usuário: (título, corpo)} — uma mensagem diferente para cada pessoa."""
    if not configurado() or not mensagens:
        return 0
    itens = [(getattr(u, 'pk', u), titulo, corpo) for u, (titulo, corpo) in mensagens.items()]

    def tarefa():
        enviados = 0
        try:
            for uid, titulo, corpo in itens:
                payload = json.dumps({'titulo': titulo, 'corpo': corpo, 'url': url, 'tag': tag or ''},
                                     ensure_ascii=False)
                enviados += _enviar_agora([uid], payload, ttl)
        finally:
            if em_segundo_plano:
                close_old_connections()
        return enviados

    if em_segundo_plano:
        transaction.on_commit(lambda: threading.Thread(target=tarefa, daemon=True).start())
        return len(itens)
    return tarefa()  # devolve quantos celulares receberam
