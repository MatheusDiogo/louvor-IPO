"""Importação de músicas a partir de um caderno de cifras em PDF (somente líderes).

1. O líder envia o PDF; cada música é convertida para ChordPro.
2. Revisa a lista (nova / atualizar / repetida), corrige tons e vê a conversão de cada uma.
3. Confirma: as músicas são criadas ou atualizadas e marcadas como "revisar".
"""
import logging
import re
import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica
from .cifra import renderizar_html
from .importador import analisar_pdf
from .models import Musica

logger = logging.getLogger(__name__)

PASTA_TEMP = 'importacoes'
TAMANHO_MAXIMO = 30 * 1024 * 1024  # 30 MB
TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')


def _caminho(token):
    if not TOKEN_RE.match(token or ''):
        raise Http404
    return f'{PASTA_TEMP}/{token}.pdf'


def _ler_temporario(token):
    caminho = _caminho(token)
    if not default_storage.exists(caminho):
        raise Http404
    with default_storage.open(caminho, 'rb') as arquivo:
        return arquivo.read()


def _limpar_antigos():
    """Remove uploads de importações abandonadas há mais de um dia."""
    try:
        _, arquivos = default_storage.listdir(PASTA_TEMP)
    except FileNotFoundError:
        return
    limite = timezone.now() - timedelta(days=1)
    for nome in arquivos:
        caminho = f'{PASTA_TEMP}/{nome}'
        try:
            if default_storage.get_modified_time(caminho) < limite:
                default_storage.delete(caminho)
        except Exception:
            logger.exception('Falha ao limpar importação antiga %s', caminho)


def _montar_plano(musicas_pdf):
    existentes = {chave_alfabetica(m.nome): m for m in Musica.objects.all()}
    vistos = {}
    plano = []
    for m in musicas_pdf:
        chave = chave_alfabetica(m.titulo)
        existente = existentes.get(chave)
        repetida_de = vistos.get(chave)
        if repetida_de:
            situacao = 'repetida'
        elif existente:
            situacao = 'atualizar'
        else:
            situacao = 'nova'
        vistos.setdefault(chave, m.numero)
        plano.append({
            'numero': m.numero,
            'titulo': m.titulo,
            'tom': m.tom,
            'avisos': m.avisos,
            'existente': existente.nome if existente else '',
            'repetida_de': repetida_de,
            'situacao': situacao,
            'selecionada': situacao != 'repetida',
        })
    return plano


@login_required
@requer_lider
def importar_pdf(request):
    if request.method != 'POST':
        return render(request, 'musicas_importar.html')

    arquivo = request.FILES.get('pdf')
    if not arquivo:
        messages.error(request, 'Selecione o arquivo PDF.')
        return redirect('importar_pdf')
    if arquivo.size > TAMANHO_MAXIMO:
        messages.error(request, 'O arquivo é muito grande (máximo de 30 MB).')
        return redirect('importar_pdf')

    dados = arquivo.read()
    try:
        musicas_pdf = analisar_pdf(dados)
    except Exception:
        logger.exception('PDF inválido na importação')
        messages.error(request, 'Não foi possível ler o arquivo. Verifique se é um PDF válido.')
        return redirect('importar_pdf')

    if not musicas_pdf:
        messages.error(request, 'Nenhuma música encontrada. Os títulos precisam estar no formato "1. Nome da música".')
        return redirect('importar_pdf')

    _limpar_antigos()
    token = uuid.uuid4().hex
    default_storage.save(_caminho(token), ContentFile(dados))

    plano = _montar_plano(musicas_pdf)
    resumo = {s: sum(1 for i in plano if i['situacao'] == s) for s in ('nova', 'atualizar', 'repetida')}
    resumo['avisos'] = sum(1 for i in plano if i['avisos'])
    return render(request, 'musicas_importar.html', {
        'plano': plano, 'resumo': resumo, 'token': token, 'nome_arquivo': arquivo.name,
    })


@login_required
@requer_lider
def importar_pdf_previa(request, token, numero):
    """Mostra como a música ficou convertida, antes de importar."""
    musica = next((m for m in analisar_pdf(_ler_temporario(token)) if m.numero == numero), None)
    if not musica:
        raise Http404
    return render(request, 'musica_importar_previa.html', {
        'musica': musica,
        'cifra_html': renderizar_html(musica.chordpro, musica.tom),
    })


@login_required
@requer_lider
@require_POST
def importar_pdf_confirmar(request):
    token = request.POST.get('token', '')
    try:
        dados = _ler_temporario(token)
    except Http404:
        messages.error(request, 'A importação expirou. Envie o PDF novamente.')
        return redirect('importar_pdf')

    selecionadas = set(request.POST.getlist('numeros'))
    existentes = {chave_alfabetica(m.nome): m for m in Musica.objects.all()}
    criadas = atualizadas = 0

    with transaction.atomic():
        for m in analisar_pdf(dados):
            if str(m.numero) not in selecionadas:
                continue
            tom = request.POST.get(f'tom_{m.numero}', m.tom).strip()[:10]
            chave = chave_alfabetica(m.titulo)
            musica = existentes.get(chave)
            if musica is None:
                musica = Musica(nome=m.titulo)
                existentes[chave] = musica
                criadas += 1
            else:
                atualizadas += 1
            musica.tom = tom
            musica.cifra = m.chordpro
            musica.revisar = True  # conversão automática: um líder deve conferir
            musica.save()

    default_storage.delete(_caminho(token))

    partes = []
    if criadas:
        partes.append(f'{criadas} música(s) nova(s)')
    if atualizadas:
        partes.append(f'{atualizadas} atualizada(s)')
    if partes:
        messages.success(request, 'Importação concluída: ' + ' e '.join(partes)
                         + '. Elas ficam marcadas como "Revisar" até serem salvas no editor.')
    else:
        messages.info(request, 'Nenhuma música foi importada.')
    return redirect('musicas')
