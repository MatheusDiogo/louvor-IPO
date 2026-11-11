"""Quando e para quem cada notificação do louvor é enviada."""
from django.contrib.auth import get_user_model
from django.utils import timezone

from . import servico

# A partir de quantas músicas o repertório do culto é considerado "definido" e a equipe é avisada.
# Depois disso, cada música adicionada/removida e cada troca de tom gera um aviso.
MUSICAS_PARA_AVISAR = 5


def eh_vocal(instrumento):
    nome = (instrumento.nome or '').lower()
    return any(p in nome for p in ('vocal', 'voz', 'canto', 'backing'))


def _equipe(escala, sem_vocal=False):
    """Integrantes ativos escalados no culto -> {usuário: instrumento}."""
    equipe = {}
    for ei in escala.integrantes.select_related('usuario', 'instrumento'):
        if not ei.usuario.is_active or (sem_vocal and eh_vocal(ei.instrumento)):
            continue
        equipe[ei.usuario] = ei.instrumento
    return equipe


def _culto_futuro(escala):
    return escala.data >= timezone.localdate()


def _url_cifras(escala):
    return f'/escalas/{escala.pk}/cifras/'


# ---------------------------------------------------------------- 3. repertório do culto

def repertorio_adicionado(escala, item, total):
    """Chamado depois de adicionar uma música ao culto (`total` = quantas músicas o culto tem agora)."""
    if not _culto_futuro(escala) or total < MUSICAS_PARA_AVISAR:
        return 0
    if total == MUSICAS_PARA_AVISAR:
        titulo = f'Músicas do culto de {escala.data:%d/%m} definidas'
        corpo = f'{total} músicas no repertório. Toque para ver as cifras e ensaiar no tom certo.'
    else:
        titulo = f'Repertório do culto de {escala.data:%d/%m} alterado'
        corpo = f'Música adicionada: {item.musica.nome}' + (f' (tom {item.tom})' if item.tom else '')
    return servico.enviar(_equipe(escala), titulo, corpo, url=_url_cifras(escala), tag=f'culto-{escala.pk}-musicas')


def repertorio_removido(escala, nome_musica, total_antes):
    if not _culto_futuro(escala) or total_antes < MUSICAS_PARA_AVISAR:
        return 0
    return servico.enviar(
        _equipe(escala), f'Repertório do culto de {escala.data:%d/%m} alterado',
        f'Música removida: {nome_musica}', url=_url_cifras(escala), tag=f'culto-{escala.pk}-musicas')


def tom_alterado(escala, item, tom_antigo):
    """Troca de tom: avisa só quem toca instrumento (o vocal não precisa)."""
    if not _culto_futuro(escala) or escala.itens.count() < MUSICAS_PARA_AVISAR or item.tom == tom_antigo:
        return 0
    return servico.enviar(
        _equipe(escala, sem_vocal=True), f'Tom alterado no culto de {escala.data:%d/%m}',
        f'{item.musica.nome}: agora em {item.tom or "tom original"}' + (f' (antes {tom_antigo})' if tom_antigo else ''),
        url=_url_cifras(escala), tag=f'culto-{escala.pk}-tom-{item.pk}')


# ---------------------------------------------------------------- 4. cadastro aguardando aprovação

def cadastro_pendente(usuario):
    lideres = get_user_model().objects.filter(is_lider=True, is_active=True)
    nome = usuario.get_full_name() or usuario.email
    return servico.enviar(lideres, 'Novo cadastro aguardando aprovação',
                          f'{nome} quer entrar no louvor. Toque para aprovar ou recusar.',
                          url='/integrantes/', tag='cadastro-pendente')


# ---------------------------------------------------------------- 5. escala do mês publicada

def escala_publicada(inicio, fim, nome_mes):
    """Aviso geral, personalizado: quem está escalado vê as próprias datas."""
    from apps.escalas.models import EscalaIntegrante

    datas = {}
    for ei in (EscalaIntegrante.objects.filter(escala__data__range=(inicio, fim), usuario__is_active=True)
               .select_related('escala', 'instrumento').order_by('escala__data')):
        datas.setdefault(ei.usuario_id, []).append(f'{ei.escala.data:%d/%m} ({ei.instrumento.nome})')

    mensagens = {}
    titulo = f'Escala de {nome_mes} publicada'
    for usuario in get_user_model().objects.filter(is_active=True, inscricoes_push__isnull=False).distinct():
        minhas = datas.get(usuario.pk)
        if minhas:
            corpo = 'Você está escalado em ' + ', '.join(minhas) + '.'
        else:
            corpo = 'Você não está escalado este mês. Toque para ver a escala completa.'
        mensagens[usuario.pk] = (titulo, corpo)
    return servico.enviar_personalizado(mensagens, url='/escalas/', tag=f'escala-{inicio:%Y-%m}')
