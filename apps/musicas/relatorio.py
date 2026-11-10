"""Relatório de músicas tocadas nos cultos de um período (somente líderes)."""
import csv
from datetime import date

import fitz  # PyMuPDF
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica, subtrair_meses
from apps.escalas.models import Escala, EscalaMusica
from .cifra_pdf import ALTURA, CINZA, LARGURA, MARGEM, PRETO, VERDE, _largura, _limpar
from .models import Musica


def _periodo(request):
    hoje = timezone.localdate()
    try:
        inicio = date.fromisoformat(request.GET.get('inicio', ''))
    except ValueError:
        inicio = subtrair_meses(hoje, 3)
    try:
        fim = date.fromisoformat(request.GET.get('fim', ''))
    except ValueError:
        fim = hoje
    return (fim, inicio) if fim < inicio else (inicio, fim)


def _dados(inicio, fim, incluir_nao_tocadas):
    contagem = {
        linha['musica']: linha
        for linha in EscalaMusica.objects.filter(escala__data__range=(inicio, fim))
        .values('musica').annotate(vezes=Count('id'), ultima=Max('escala__data'))
    }
    linhas = []
    for musica in Musica.objects.all():
        dados = contagem.get(musica.id)
        if not dados and not incluir_nao_tocadas:
            continue
        linhas.append({
            'musica': musica,
            'vezes': dados['vezes'] if dados else 0,
            'ultima': dados['ultima'] if dados else None,
        })
    linhas.sort(key=lambda l: (-l['vezes'], chave_alfabetica(l['musica'].nome)))
    cultos = Escala.objects.filter(data__range=(inicio, fim), itens__isnull=False).distinct().count()
    return linhas, cultos


def _csv(linhas, inicio, fim):
    resposta = HttpResponse(content_type='text/csv; charset=utf-8')
    resposta['Content-Disposition'] = f'attachment; filename="musicas-tocadas-{inicio}-a-{fim}.csv"'
    resposta.write('﻿')  # BOM: o Excel reconhece os acentos
    escritor = csv.writer(resposta, delimiter=';')
    escritor.writerow(['Posição', 'Música', 'Tom original', 'Vezes tocada', 'Última vez'])
    for posicao, linha in enumerate(linhas, start=1):
        escritor.writerow([
            posicao, linha['musica'].nome, linha['musica'].tom, linha['vezes'],
            linha['ultima'].strftime('%d/%m/%Y') if linha['ultima'] else '',
        ])
    return resposta


def _pdf(linhas, inicio, fim, cultos):
    doc = fitz.open()
    colunas = [(MARGEM, 'Nº'), (MARGEM + 32, 'Música'), (LARGURA - MARGEM - 175, 'Tom'),
               (LARGURA - MARGEM - 125, 'Vezes'), (LARGURA - MARGEM - 70, 'Última vez')]
    largura_nome = colunas[2][0] - colunas[1][0] - 8
    pagina, y = None, 0

    def nova_pagina():
        nonlocal pagina, y
        pagina = doc.new_page(width=LARGURA, height=ALTURA)
        y = MARGEM
        if len(doc) == 1:
            pagina.insert_text((MARGEM, y + 18), 'Músicas tocadas nos cultos', fontname='hebo', fontsize=18, color=VERDE)
            y += 30
            resumo = f'{inicio:%d/%m/%Y} a {fim:%d/%m/%Y} - {cultos} culto(s) - {len(linhas)} música(s)'
            pagina.insert_text((MARGEM, y + 10), _limpar(resumo), fontname='helv', fontsize=10, color=CINZA)
            y += 26
        for x, titulo in colunas:
            pagina.insert_text((x, y + 10), titulo, fontname='hebo', fontsize=9.5, color=CINZA)
        y += 16
        pagina.draw_line((MARGEM, y), (LARGURA - MARGEM, y), color=(0.85, 0.88, 0.86), width=0.8)
        y += 6

    nova_pagina()
    for posicao, linha in enumerate(linhas, start=1):
        if y + 18 > ALTURA - MARGEM:
            nova_pagina()
        nome = linha['musica'].nome
        while _largura(nome, 'helv', 10.5) > largura_nome and len(nome) > 4:
            nome = nome[:-2].rstrip() + '…'
        valores = [str(posicao), nome, linha['musica'].tom or '-', str(linha['vezes']),
                   linha['ultima'].strftime('%d/%m/%Y') if linha['ultima'] else '-']
        for coluna, ((x, _), valor) in enumerate(zip(colunas, valores)):
            fonte = 'hebo' if coluna == 3 and linha['vezes'] else 'helv'
            pagina.insert_text((x, y + 11), _limpar(valor), fontname=fonte, fontsize=10.5,
                               color=PRETO if linha['vezes'] else CINZA)
        y += 18
    if not linhas:
        pagina.insert_text((MARGEM, y + 14), 'Nenhuma música tocada no período.', fontname='helv', fontsize=11)

    for numero, p in enumerate(doc, start=1):
        p.insert_text((MARGEM, ALTURA - 20), f'Louvor IPO - {numero}/{len(doc)}', fontname='helv', fontsize=8, color=CINZA)
    dados = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    resposta = HttpResponse(dados, content_type='application/pdf')
    resposta['Content-Disposition'] = f'inline; filename="musicas-tocadas-{inicio}-a-{fim}.pdf"'
    return resposta


@login_required
@requer_lider
def relatorio_musicas(request):
    inicio, fim = _periodo(request)
    incluir_nao_tocadas = request.GET.get('todas') == '1'
    linhas, cultos = _dados(inicio, fim, incluir_nao_tocadas)

    formato = request.GET.get('formato')
    if formato == 'csv':
        return _csv(linhas, inicio, fim)
    if formato == 'pdf':
        return _pdf(linhas, inicio, fim, cultos)

    maximo = max((l['vezes'] for l in linhas), default=0)
    return render(request, 'musicas_relatorio.html', {
        'inicio': inicio,
        'fim': fim,
        'todas': incluir_nao_tocadas,
        'linhas': linhas,
        'cultos': cultos,
        'total_execucoes': sum(l['vezes'] for l in linhas),
        'maximo': maximo,
        'consulta': request.GET.urlencode(),
    })
