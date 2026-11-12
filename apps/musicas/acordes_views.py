"""Tela dos líderes para cadastrar e ajustar os desenhos de acordes (violão) e as grafias."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.decorators import requer_lider
from .acordes import (
    FORMULAS, ROTULOS_TIPOS, analisar, dedos_simples, gerar_com_baixo, mapa_de_nomes, normalizar_grafia,
    ordem_de_exibicao,
)
from .cifra import ACORDE_RE
from .models import NOMES_NOTAS, DesenhoAcorde, NomeAcorde

CAMPOS = ('id', 'raiz', 'tipo', 'baixo', 'casas', 'dedos', 'pestanas', 'ordem', 'origem', 'ativo')


def _tipos():
    return [(tipo, ROTULOS_TIPOS.get(tipo, tipo)) for tipo in FORMULAS]


@login_required
@requer_lider
def acordes_view(request):
    tipos = _tipos()
    posicao = {tipo: i for i, (tipo, _) in enumerate(tipos)}
    grafias = sorted(NomeAcorde.objects.all(), key=lambda n: (posicao.get(n.tipo, 99), n.escrita))
    for grafia in grafias:
        grafia.rotulo = ROTULOS_TIPOS.get(grafia.tipo, grafia.tipo)
    return render(request, 'acordes.html', {
        'grafias': grafias,
        'tipos': tipos,
        'busca': request.GET.get('acorde', ''),
    })


def _grupo(raiz, tipo, baixo):
    return DesenhoAcorde.objects.filter(instrumento='violao', raiz=raiz, tipo=tipo, baixo=baixo)


def _dados_do_acorde(nome):
    analise = analisar(nome.strip(), mapa_de_nomes())
    if analise is None:
        return {'ok': False, 'erro': f'"{nome}" não parece um acorde. Escreva como na cifra: A, Bm7, B/D#...'}
    raiz, tipo, baixo = analise
    if not tipo:
        escrita = ACORDE_RE.match(nome.strip()).group('sufixo')
        return {'ok': False, 'grafia': escrita,
                'erro': f'O site não conhece a grafia "{escrita}". Cadastre-a em "Grafias", mais abaixo.'}
    desenhos = sorted(_grupo(raiz, tipo, baixo).values(*CAMPOS), key=ordem_de_exibicao)
    gerados = []
    if baixo is not None and not any(d['ativo'] for d in desenhos):
        # Desenhos que o site monta sozinho (ainda não estão na tabela)
        for d in sorted(_grupo(raiz, tipo, None).filter(ativo=True).values(*CAMPOS), key=ordem_de_exibicao):
            casas = gerar_com_baixo(d['casas'], baixo, raiz)
            if casas and all(casas != g['casas'] for g in gerados):
                dedos, pestanas = dedos_simples(casas)
                gerados.append({'casas': casas, 'dedos': dedos, 'pestanas': pestanas, 'gerado': True})
    escrito = ACORDE_RE.match(nome.strip())  # nomes das notas como foram escritos (D# e não Eb)
    return {
        'ok': True, 'nome': nome.strip(), 'raiz': raiz, 'tipo': tipo, 'baixo': baixo,
        'descricao': ' · '.join(filter(None, [
            escrito.group('raiz'), ROTULOS_TIPOS.get(tipo, tipo),
            f'baixo em {escrito.group("baixo")}' if baixo is not None else '',
        ])),
        'desenhos': desenhos, 'gerados': gerados,
    }


@login_required
@requer_lider
@require_GET
def acordes_buscar(request):
    return JsonResponse(_dados_do_acorde(request.GET.get('nome', '')))


def _validar(dados):
    """Confere o desenho enviado pelo editor. Devolve (campos, erro)."""
    try:
        casas = [int(c) for c in dados['casas']]
        dedos = [int(d) for d in dados.get('dedos') or [0] * 6]
        pestanas = sorted({int(p) for p in dados.get('pestanas') or []})
        raiz = int(dados['raiz'])
        baixo = None if dados.get('baixo') in (None, '') else int(dados['baixo'])
        tipo = str(dados['tipo'])
    except (KeyError, TypeError, ValueError):
        return None, 'Dados inválidos.'
    if len(casas) != 6 or len(dedos) != 6:
        return None, 'O desenho precisa ter as 6 cordas.'
    if any(c < -1 or c > 24 for c in casas) or any(d < 0 or d > 4 for d in dedos):
        return None, 'Casa ou dedo inválido.'
    if sum(1 for c in casas if c >= 0) < 2:
        return None, 'Marque pelo menos duas cordas tocadas.'
    if not 0 <= raiz <= 11 or (baixo is not None and not 0 <= baixo <= 11) or tipo not in FORMULAS:
        return None, 'Acorde inválido.'
    pestanas = [p for p in pestanas if sum(1 for c in casas if c == p) >= 2]
    dedos = [d if c > 0 else 0 for c, d in zip(casas, dedos)]
    return {'raiz': raiz, 'tipo': tipo, 'baixo': baixo, 'casas': casas, 'dedos': dedos, 'pestanas': pestanas}, None


@login_required
@requer_lider
@require_POST
def acordes_salvar(request):
    """Cria ou altera um desenho. Alterar um desenho da base cria uma cópia da equipe e esconde o original."""
    try:
        dados = json.loads(request.body or '{}')
    except ValueError:
        return JsonResponse({'ok': False, 'erro': 'Dados inválidos.'}, status=400)
    campos, erro = _validar(dados)
    if erro:
        return JsonResponse({'ok': False, 'erro': erro}, status=400)

    with transaction.atomic():
        original = DesenhoAcorde.objects.filter(pk=dados.get('id')).first() if dados.get('id') else None
        if original and original.origem == 'equipe':
            for campo, valor in campos.items():
                setattr(original, campo, valor)
            original.save()
        else:
            ordem = original.ordem if original else 0  # desenho novo entra em primeiro no "Variar"
            DesenhoAcorde.objects.create(instrumento='violao', origem='equipe', ativo=True, ordem=ordem, **campos)
            if original:
                original.ativo = False
                original.save(update_fields=['ativo'])
    return JsonResponse({'ok': True})


@login_required
@requer_lider
@require_POST
def acordes_ativo(request, pk):
    desenho = get_object_or_404(DesenhoAcorde, pk=pk)
    desenho.ativo = not desenho.ativo
    desenho.save(update_fields=['ativo'])
    return JsonResponse({'ok': True, 'ativo': desenho.ativo})


@login_required
@requer_lider
@require_POST
def acordes_mover(request, pk):
    """Troca a posição do desenho com o vizinho na ordem do "Variar" (direcao = -1 ou 1)."""
    desenho = get_object_or_404(DesenhoAcorde, pk=pk)
    direcao = -1 if request.POST.get('direcao') == '-1' else 1
    with transaction.atomic():
        grupo = sorted(_grupo(desenho.raiz, desenho.tipo, desenho.baixo),
                       key=lambda d: ordem_de_exibicao({'ordem': d.ordem, 'origem': d.origem, 'id': d.id}))
        indice = next(i for i, d in enumerate(grupo) if d.pk == desenho.pk)
        alvo = indice + direcao
        if 0 <= alvo < len(grupo):
            grupo[indice], grupo[alvo] = grupo[alvo], grupo[indice]
            for posicao, item in enumerate(grupo, start=1):
                if item.ordem != posicao:
                    item.ordem = posicao
                    item.save(update_fields=['ordem'])
    return JsonResponse({'ok': True})


@login_required
@requer_lider
@require_POST
def acordes_excluir(request, pk):
    desenho = get_object_or_404(DesenhoAcorde, pk=pk)
    if desenho.origem != 'equipe':
        return JsonResponse({'ok': False, 'erro': 'Desenhos da base não são apagados; use "Esconder".'}, status=400)
    desenho.delete()
    return JsonResponse({'ok': True})


@login_required
@requer_lider
@require_POST
def grafia_salvar(request):
    digitada = request.POST.get('escrita', '').strip()
    escrita = normalizar_grafia(digitada)
    tipo = request.POST.get('tipo', '')
    if tipo not in FORMULAS:
        messages.error(request, 'Escolha o tipo do acorde.')
    elif len(digitada) > 20 or ' ' in digitada:
        messages.error(request, 'A grafia deve ser curta e sem espaços (ex.: 4/7, 7M, m7(b5)).')
    else:
        existente = NomeAcorde.objects.filter(escrita=escrita).first()
        if existente and existente.tipo == tipo:
            messages.info(request, f'"{digitada}" já é reconhecida (como "{escrita}" = {ROTULOS_TIPOS.get(tipo, tipo)}).')
        else:
            NomeAcorde.objects.update_or_create(escrita=escrita, defaults={'tipo': tipo, 'origem': 'equipe'})
            como = f' (guardada como "{escrita}")' if escrita != digitada else ''
            messages.success(request, f'Grafia "{digitada or "(vazia)"}" salva{como}: '
                                      f'A{digitada} = A {ROTULOS_TIPOS.get(tipo, tipo)}.')
    return redirect('/musicas/acordes/#grafias')


@login_required
@requer_lider
@require_POST
def grafia_excluir(request, pk):
    grafia = get_object_or_404(NomeAcorde, pk=pk)
    grafia.delete()
    messages.success(request, f'Grafia "{grafia.escrita}" removida.')
    return redirect('/musicas/acordes/#grafias')
