"""Escala de integrantes: quem toca/canta em cada culto (acesso somente de líderes)."""
import calendar
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica
from apps.instrumentos.models import Instrumento
from .models import Escala, EscalaIntegrante

Usuario = get_user_model()

LIMITE_ESCALAS_MES = 3  # a partir de quantas vezes no mês o integrante fica em vermelho


# ---------------------------------------------------------------- helpers

def _nomes_curtos(usuarios):
    """Primeiro nome; se houver dois iguais, acrescenta a inicial do sobrenome."""
    base = {u.id: (u.first_name or u.username).strip() for u in usuarios}
    repetidos = Counter(n.lower() for n in base.values())
    nomes = {}
    for u in usuarios:
        nome = base[u.id]
        if repetidos[nome.lower()] > 1 and u.last_name:
            nome = f"{nome} {u.last_name.strip()[0]}."
        nomes[u.id] = nome
    return nomes


def _juntar_nomes(nomes):
    """['A', 'B', 'C'] -> 'A, B e C' (como na planilha)."""
    if len(nomes) <= 1:
        return ''.join(nomes)
    return ', '.join(nomes[:-1]) + ' e ' + nomes[-1]


def _mes_da_requisicao(valor):
    hoje = timezone.localdate()
    try:
        ano, mes = (int(p) for p in (valor or '').split('-'))
        return date(ano, mes, 1)
    except (ValueError, TypeError):
        return hoje.replace(day=1)


def _fim_do_mes(inicio):
    return inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])


def _url_mes(dia):
    return f"{reverse('escala_equipe')}?mes={dia:%Y-%m}"


def _montar_linhas(escalas, instrumentos, nomes):
    """Para cada culto, a lista de células (uma por instrumento) com os integrantes escalados."""
    linhas = []
    for escala in escalas:
        por_instrumento = defaultdict(list)
        for ei in sorted(escala.integrantes.all(), key=lambda x: x.pk):  # mantém a ordem de inclusão
            por_instrumento[ei.instrumento_id].append(ei.usuario_id)
        celulas = []
        for inst in instrumentos:
            membros = [
                {
                    'id': uid,
                    'nome': nomes.get(uid, '?'),
                    'ministrante': uid == escala.ministrante_id,
                }
                for uid in por_instrumento.get(inst.id, [])
            ]
            celulas.append({'instrumento': inst, 'membros': membros})
        linhas.append({'escala': escala, 'celulas': celulas})
    return linhas


def _escalas_no_periodo(inicio, fim):
    return (
        Escala.objects.filter(data__range=(inicio, fim))
        .order_by('data')
        .prefetch_related('integrantes')
    )


# ---------------------------------------------------------------- views

@login_required
@requer_lider
def escala_equipe(request):
    """Grade do mês: datas nas linhas, instrumentos nas colunas."""
    inicio = _mes_da_requisicao(request.GET.get('mes'))
    fim = _fim_do_mes(inicio)

    instrumentos = list(Instrumento.objects.all())
    usuarios = list(Usuario.objects.filter(is_active=True).prefetch_related('instrumentos'))
    nomes = _nomes_curtos(list(Usuario.objects.all()))
    escalas = list(_escalas_no_periodo(inicio, fim))
    linhas = _montar_linhas(escalas, instrumentos, nomes)

    # Quantos cultos diferentes cada integrante tem no mês
    contagem = Counter()
    for escala in escalas:
        for uid in {ei.usuario_id for ei in escala.integrantes.all()}:
            contagem[uid] += 1

    for linha in linhas:
        for celula in linha['celulas']:
            for m in celula['membros']:
                m['vezes'] = contagem[m['id']]
                m['alerta'] = contagem[m['id']] >= LIMITE_ESCALAS_MES

    alertas = sorted(
        ({'nome': nomes[uid], 'vezes': n} for uid, n in contagem.items()
         if n >= LIMITE_ESCALAS_MES and uid in nomes),
        key=lambda a: (-a['vezes'], chave_alfabetica(a['nome'])),
    )

    nomes_instrumentos = {inst.id: inst.nome for inst in instrumentos}

    # Dados usados pelo modal de edição de cada célula
    dados_modal = {
        'instrumentos': {
            inst.id: {
                'nome': inst.nome,
                'membros': sorted(
                    ({'id': u.id, 'nome': nomes[u.id]} for u in usuarios
                     if any(i.id == inst.id for i in u.instrumentos.all())),
                    key=lambda m: chave_alfabetica(m['nome']),
                ),
            }
            for inst in instrumentos
        },
        'celulas': {
            f"{l['escala'].id}-{c['instrumento'].id}": [m['id'] for m in c['membros']]
            for l in linhas for c in l['celulas']
        },
        'ministrante': {e.id: e.ministrante_id for e in escalas},
        # quem já está em algum instrumento em cada culto: {culto: {pessoa: [instrumento, nome do instrumento]}}
        'ocupados': {
            e.id: {ei.usuario_id: [ei.instrumento_id, nomes_instrumentos.get(ei.instrumento_id, '')]
                   for ei in e.integrantes.all()}
            for e in escalas
        },
        'datas': {e.id: e.data.strftime('%d/%m') for e in escalas},
        'contagem': dict(contagem),
        'limite': LIMITE_ESCALAS_MES,
    }

    anterior = (inicio - timedelta(days=1)).replace(day=1)
    proximo = fim + timedelta(days=1)

    return render(request, 'escalas/equipe.html', {
        'mes': inicio,
        'mes_anterior': anterior,
        'mes_proximo': proximo,
        'instrumentos': instrumentos,
        'linhas': linhas,
        'alertas': alertas,
        'dados_modal': dados_modal,
        'limite': LIMITE_ESCALAS_MES,
        'hoje': timezone.localdate(),
    })


@login_required
@requer_lider
@require_POST
def escala_equipe_adicionar_data(request):
    """Adiciona uma data à escala; cria o culto correspondente se ainda não existir."""
    try:
        dia = date.fromisoformat(request.POST.get('data', ''))
    except ValueError:
        messages.error(request, 'Informe uma data válida.')
        return redirect('escala_equipe')

    _, criado = Escala.objects.get_or_create(data=dia)
    if criado:
        messages.success(request, f'Culto de {dia:%d/%m/%Y} criado. Agora escale os integrantes.')
    else:
        messages.info(request, f'O culto de {dia:%d/%m/%Y} já existia.')
    return redirect(_url_mes(dia))


@login_required
@requer_lider
@require_POST
def escala_equipe_celula(request, pk):
    """Salva os integrantes de um instrumento em um culto (e o ministrante, se marcado)."""
    escala = get_object_or_404(Escala, pk=pk)
    instrumento = get_object_or_404(Instrumento, pk=request.POST.get('instrumento_id'))

    # Só aceita quem tem o instrumento cadastrado
    permitidos = set(instrumento.musicos.filter(is_active=True).values_list('id', flat=True))

    # Uma pessoa só pode estar em um instrumento por culto
    em_outro_instrumento = {
        ei.usuario_id: ei for ei in EscalaIntegrante.objects
        .filter(escala=escala).exclude(instrumento=instrumento).select_related('usuario', 'instrumento')
    }
    selecionados, recusados = [], []
    for valor in request.POST.getlist('usuarios'):
        if not valor.isdigit() or int(valor) not in permitidos or int(valor) in selecionados:
            continue
        if int(valor) in em_outro_instrumento:
            recusados.append(em_outro_instrumento[int(valor)])
            continue
        selecionados.append(int(valor))
    for ei in recusados:
        nome = ei.usuario.first_name or ei.usuario.username
        messages.error(request, f'{nome} já está em {ei.instrumento.nome} no culto de {escala.data:%d/%m}. '
                                f'Tire de lá antes de colocar em {instrumento.nome}.')

    ministrante = request.POST.get('ministrante', '')
    ministrante = int(ministrante) if ministrante.isdigit() else None

    with transaction.atomic():
        atuais = EscalaIntegrante.objects.filter(escala=escala, instrumento=instrumento)
        antes = set(atuais.values_list('usuario_id', flat=True))

        atuais.exclude(usuario_id__in=selecionados).delete()
        for uid in selecionados:  # mantém quem já estava (e a ordem), adiciona os novos no fim
            if uid not in antes:
                EscalaIntegrante.objects.create(escala=escala, instrumento=instrumento, usuario_id=uid)

        if ministrante in selecionados:
            escala.ministrante_id = ministrante
        elif escala.ministrante_id in antes:
            # o ministrante estava nesta célula e foi desmarcado/removido
            escala.ministrante = None
        if escala.ministrante_id and not escala.integrantes.filter(usuario_id=escala.ministrante_id).exists():
            escala.ministrante = None
        escala.save(update_fields=['ministrante'])

    return redirect(_url_mes(escala.data))


@login_required
@requer_lider
def escala_equipe_exportar(request):
    """Tabela no estilo da planilha (um bloco por mês) para baixar como imagem."""
    hoje = timezone.localdate()
    try:
        inicio = date.fromisoformat(request.GET.get('inicio', ''))
    except ValueError:
        inicio = hoje.replace(day=1)
    try:
        fim = date.fromisoformat(request.GET.get('fim', ''))
    except ValueError:
        fim = _fim_do_mes(inicio)
    if fim < inicio:
        inicio, fim = fim, inicio

    instrumentos = list(Instrumento.objects.all())
    escalas = list(_escalas_no_periodo(inicio, fim))
    nomes = _nomes_curtos(list(Usuario.objects.all()))
    linhas = _montar_linhas(escalas, instrumentos, nomes)

    for linha in linhas:
        for celula in linha['celulas']:
            celula['texto'] = _juntar_nomes([
                m['nome'] + ('*' if m['ministrante'] else '') for m in celula['membros']
            ]) or '-'

    meses = []
    for linha in linhas:
        chave = (linha['escala'].data.year, linha['escala'].data.month)
        if not meses or meses[-1]['chave'] != chave:
            meses.append({'chave': chave, 'data': linha['escala'].data, 'linhas': []})
        meses[-1]['linhas'].append(linha)

    return render(request, 'escalas/equipe_exportar.html', {
        'inicio': inicio,
        'fim': fim,
        'instrumentos': instrumentos,
        'meses': meses,
    })
