"""Escala de integrantes: quem toca/canta em cada culto (acesso somente de líderes)."""
import calendar
import json
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica
from apps.instrumentos.models import Instrumento
from apps.notificacoes import avisos, servico
from .models import Escala, EscalaIntegrante, PublicacaoEscala

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
        'nomes': nomes,
        'contagem': dict(contagem),
        'limite': LIMITE_ESCALAS_MES,
    }

    publicacao = PublicacaoEscala.objects.filter(mes=inicio).first()
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
        'publicacao': publicacao,
        'notificacoes_ativas': servico.configurado(),
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


class ErroEscala(Exception):
    pass


def _validar_culto(escala, celulas, ministrante, instrumentos, nomes):
    """Confere as células enviadas para um culto. Devolve {instrumento: [usuários]} e o ministrante."""
    resultado = {}
    vistos = {}  # usuário -> instrumento (uma pessoa por instrumento por culto)
    atuais = defaultdict(set)
    for ei in escala.integrantes.all():
        atuais[ei.instrumento_id].add(ei.usuario_id)

    for inst_id_txt, usuarios in (celulas or {}).items():
        inst = instrumentos.get(int(inst_id_txt)) if str(inst_id_txt).isdigit() else None
        if inst is None:
            raise ErroEscala('Instrumento inválido.')
        # Pode: quem tem o instrumento cadastrado (ativo) ou quem já estava na célula
        permitidos = inst.permitidos | atuais[inst.id]
        lista = []
        for uid in usuarios or []:
            uid = int(uid) if str(uid).isdigit() else None
            if uid is None or uid in lista:
                continue
            if uid not in permitidos:
                raise ErroEscala(f'{nomes.get(uid, "Integrante")} não tem {inst.nome} cadastrado.')
            if uid in vistos and vistos[uid] != inst.id:
                raise ErroEscala(f'{nomes.get(uid, "Integrante")} está em {instrumentos[vistos[uid]].nome} e em '
                                 f'{inst.nome} no culto de {escala.data:%d/%m}. Deixe em um só.')
            vistos[uid] = inst.id
            lista.append(uid)
        resultado[inst.id] = lista

    # Instrumentos não enviados continuam como estão (e também contam para a regra de um por culto)
    for inst_id, usuarios in atuais.items():
        if inst_id in resultado:
            continue
        for uid in usuarios:
            if uid in vistos and vistos[uid] != inst_id:
                raise ErroEscala(f'{nomes.get(uid, "Integrante")} já está em {instrumentos[inst_id].nome} '
                                 f'no culto de {escala.data:%d/%m}.')
            vistos[uid] = inst_id

    ministrante = int(ministrante) if str(ministrante or '').isdigit() else None
    if ministrante not in vistos:
        ministrante = None  # ministrante precisa estar escalado no culto
    return resultado, ministrante


@login_required
@requer_lider
@require_POST
def escala_equipe_salvar(request):
    """Salva de uma vez todas as alterações feitas na tela de Escalas (um único envio).

    Corpo (JSON): {"cultos": {"<id do culto>": {"celulas": {"<id do instrumento>": [ids]}, "ministrante": id|null}}}
    Se algo for inválido, nada é gravado.
    """
    try:
        dados = json.loads(request.body or '{}')
        cultos = dados.get('cultos') or {}
        if not isinstance(cultos, dict):
            raise ValueError
    except ValueError:
        return JsonResponse({'ok': False, 'erro': 'Dados inválidos.'}, status=400)

    instrumentos = {}
    for inst in Instrumento.objects.prefetch_related('musicos'):
        inst.permitidos = {u.id for u in inst.musicos.all() if u.is_active}
        instrumentos[inst.id] = inst
    nomes = _nomes_curtos(list(Usuario.objects.all()))
    escalas = {e.id: e for e in Escala.objects.filter(pk__in=[k for k in cultos if str(k).isdigit()])
               .prefetch_related('integrantes')}

    try:
        planos = []
        for escala_id, culto in cultos.items():
            escala = escalas.get(int(escala_id)) if str(escala_id).isdigit() else None
            if escala is None:
                raise ErroEscala('Um dos cultos não existe mais. Recarregue a página.')
            celulas, ministrante = _validar_culto(escala, culto.get('celulas'), culto.get('ministrante'),
                                                  instrumentos, nomes)
            planos.append((escala, celulas, ministrante))
    except ErroEscala as erro:
        return JsonResponse({'ok': False, 'erro': str(erro)}, status=400)

    with transaction.atomic():
        for escala, celulas, ministrante in planos:
            for inst_id, usuarios in celulas.items():
                atuais = EscalaIntegrante.objects.filter(escala=escala, instrumento_id=inst_id)
                antes = set(atuais.values_list('usuario_id', flat=True))
                atuais.exclude(usuario_id__in=usuarios).delete()
                for uid in usuarios:  # mantém quem já estava (e a ordem); novos entram no fim
                    if uid not in antes:
                        EscalaIntegrante.objects.create(escala=escala, instrumento_id=inst_id, usuario_id=uid)
            if escala.ministrante_id != ministrante:
                escala.ministrante_id = ministrante
                escala.save(update_fields=['ministrante'])

    total = len(planos)
    messages.success(request, f'Escala salva ({total} culto{"s" if total != 1 else ""} alterado{"s" if total != 1 else ""}).')
    return JsonResponse({'ok': True})


@login_required
@requer_lider
@require_POST
def escala_equipe_publicar(request):
    """Publica a escala do mês: todos recebem uma notificação (quem está escalado vê as suas datas)."""
    inicio = _mes_da_requisicao(request.POST.get('mes'))
    fim = _fim_do_mes(inicio)
    if not Escala.objects.filter(data__range=(inicio, fim)).exists():
        messages.error(request, 'Não há cultos neste mês para publicar.')
        return redirect(_url_mes(inicio))

    from django.utils.formats import date_format
    nome_mes = date_format(inicio, 'F').lower()
    PublicacaoEscala.objects.update_or_create(mes=inicio, defaults={'publicada_por': request.user})
    avisados = avisos.escala_publicada(inicio, fim, nome_mes)
    if servico.configurado():
        messages.success(request, f'Escala de {nome_mes} publicada: {avisados} pessoa(s) com notificações ativadas foram avisadas.')
    else:
        messages.success(request, f'Escala de {nome_mes} marcada como publicada (notificações ainda não configuradas no servidor).')
    return redirect(_url_mes(inicio))


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
