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


# ---------------------------------------------------------------- 6. escala alterada depois de publicada

def retrato_escalas(escala_ids):
    """Como estão os cultos agora: {id do culto: ({usuário: instrumento}, ministrante)}."""
    from apps.escalas.models import Escala, EscalaIntegrante

    retrato = {pk: ({}, ministrante) for pk, ministrante in
               Escala.objects.filter(pk__in=escala_ids).values_list('pk', 'ministrante_id')}
    for escala_id, usuario_id, instrumento_id in (EscalaIntegrante.objects.filter(escala_id__in=escala_ids)
                                                  .values_list('escala_id', 'usuario_id', 'instrumento_id')):
        retrato[escala_id][0][usuario_id] = instrumento_id
    return retrato


def escala_alterada(escalas, antes, depois, autor=None):
    """Depois de salvar a escala: avisa só quem teve a sua escala mudada (entrou, saiu, trocou de
    instrumento ou de ministração). Só para cultos futuros de meses já publicados — antes da
    publicação, o aviso geral do "Publicar escala" já conta tudo. Quem salvou não é avisado."""
    from apps.escalas.models import PublicacaoEscala
    from apps.instrumentos.models import Instrumento

    publicados = set(PublicacaoEscala.objects.values_list('mes', flat=True))
    nomes = dict(Instrumento.objects.values_list('pk', 'nome'))
    frases = {}  # usuário -> ["Culto de 16/11: você foi escalado em Violão e vai ministrar", ...]

    for escala in sorted(escalas, key=lambda e: e.data):
        if not _culto_futuro(escala) or escala.data.replace(day=1) not in publicados:
            continue
        equipe_antes, ministrante_antes = antes.get(escala.pk, ({}, None))
        equipe_depois, ministrante_depois = depois.get(escala.pk, ({}, None))
        mudancas = {}
        for uid in set(equipe_antes) | set(equipe_depois):
            de, para = equipe_antes.get(uid), equipe_depois.get(uid)
            if de is None:
                mudancas.setdefault(uid, []).append(f'foi escalado em {nomes.get(para, "?")}')
            elif para is None:
                mudancas.setdefault(uid, []).append('saiu da escala')
            elif de != para:
                mudancas.setdefault(uid, []).append(f'mudou para {nomes.get(para, "?")} (antes {nomes.get(de, "?")})')
        if ministrante_depois != ministrante_antes:
            if ministrante_depois:
                mudancas.setdefault(ministrante_depois, []).append('vai ministrar')
            if ministrante_antes and ministrante_antes in equipe_depois:
                mudancas.setdefault(ministrante_antes, []).append('não vai mais ministrar')
        for uid, partes in mudancas.items():
            frases.setdefault(uid, []).append(f'Culto de {escala.data:%d/%m}: você ' + ' e '.join(partes))

    autor_id = getattr(autor, 'pk', autor)
    avisar = (get_user_model().objects.filter(pk__in=frases, is_active=True, inscricoes_push__isnull=False)
              .exclude(pk=autor_id).distinct())
    mensagens = {u.pk: ('Sua escala mudou', '. '.join(frases[u.pk]) + '.') for u in avisar}
    return servico.enviar_personalizado(mensagens, url='/escalas/')
