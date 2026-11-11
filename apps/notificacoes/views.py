import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import servico
from .models import InscricaoPush


def _corpo(request):
    try:
        return json.loads(request.body or '{}')
    except ValueError:
        return {}


@login_required
@require_POST
def inscrever(request):
    """Guarda (ou atualiza) o endereço de notificação deste celular para o usuário logado."""
    dados = _corpo(request)
    endpoint = str(dados.get('endpoint') or '')
    chaves = dados.get('keys') or {}
    if not endpoint.startswith('https://') or len(endpoint) > 600 or not chaves.get('p256dh') or not chaves.get('auth'):
        return JsonResponse({'ok': False, 'erro': 'Inscrição inválida.'}, status=400)
    InscricaoPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'usuario': request.user,  # o celular passa a ser de quem está logado nele agora
            'p256dh': str(chaves['p256dh'])[:200],
            'auth': str(chaves['auth'])[:100],
            'navegador': request.META.get('HTTP_USER_AGENT', '')[:300],
        },
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def cancelar(request):
    endpoint = str(_corpo(request).get('endpoint') or '')
    InscricaoPush.objects.filter(endpoint=endpoint, usuario=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def testar(request):
    enviados = servico.enviar([request.user], 'Notificações ativadas ✅',
                              'Tudo certo! Você vai receber os avisos das músicas do culto e da escala.',
                              url='/home/', tag='teste', em_segundo_plano=False)
    return JsonResponse({'ok': bool(enviados), 'enviados': enviados})
