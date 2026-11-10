"""Converte um caderno de cifras em PDF (acordes em cima da letra) para ChordPro.

Formato esperado (o caderno do Louvor IPO):
  - cada música começa com o título numerado em fonte maior: "12. Salmo 63"
  - logo abaixo vem "Tom: G" e, opcionalmente, "Intro: ..."
  - acordes ficam numa linha acima da letra; o refrão está em itálico
  - pode haver duas colunas por página e músicas que continuam na coluna/página seguinte
  - o sumário no fim do arquivo é ignorado

Os acordes são encaixados na sílaba certa usando a posição (x) de cada caractere no PDF.
"""
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from .cifra import eh_linha_de_acordes, eh_rotulo

TITULO_RE = re.compile(r'^\s*(\d{1,4})\s*[.)-]\s*(\S.*?)\s*$')
TOM_RE = re.compile(r'^\s*Tom\s*:\s*(.*?)\s*$', re.IGNORECASE)
SUMARIO_RE = re.compile(r'^\s*(sum[aá]rio|[ií]ndice)\s*$', re.IGNORECASE)
ITALICO = 2   # flags de fonte do PyMuPDF
NEGRITO = 16


@dataclass
class _Linha:
    pagina: int
    coluna: int
    rect: fitz.Rect
    chars: list      # [(x0, x1, caractere)]
    tamanho: float
    italico: bool
    negrito: bool

    @property
    def texto(self):
        return ''.join(c for _, _, c in self.chars)


@dataclass
class MusicaPDF:
    numero: int
    titulo: str
    tom: str = ''
    linhas: list = field(default_factory=list)
    chordpro: str = ''
    avisos: list = field(default_factory=list)


def _ler_linhas(doc):
    """Linhas de texto em ordem de leitura (página, coluna, altura), até o sumário."""
    linhas = []
    for pno, page in enumerate(doc):
        meio = page.rect.width / 2
        rodape = page.rect.height * 0.9
        da_pagina = []
        for bloco in page.get_text('rawdict')['blocks']:
            if bloco.get('type') != 0:
                continue
            for linha in bloco['lines']:
                chars, tamanhos = [], []
                italico = negrito = False
                for span in linha['spans']:
                    for ch in span['chars']:
                        chars.append((ch['bbox'][0], ch['bbox'][2], ch['c']))
                    if ''.join(c['c'] for c in span['chars']).strip():
                        tamanhos.append(span['size'])
                        fonte = span['font'].lower()
                        italico = italico or bool(span['flags'] & ITALICO) or 'italic' in fonte
                        negrito = negrito or bool(span['flags'] & NEGRITO) or 'bold' in fonte
                texto = ''.join(c for _, _, c in chars).strip()
                if not texto:
                    continue
                rect = fitz.Rect(linha['bbox'])
                if rect.y0 > rodape and texto.isdigit():
                    continue  # número da página
                da_pagina.append(_Linha(pno, 0 if rect.x0 < meio else 1, rect, chars,
                                        max(tamanhos or [0]), italico, negrito))
        if any(SUMARIO_RE.match(l.texto) for l in da_pagina):
            break  # o sumário e o que vem depois não são músicas
        da_pagina.sort(key=lambda l: (l.coluna, round(l.rect.y0, 1), l.rect.x0))
        linhas.extend(da_pagina)
    return linhas


def _tamanhos(linhas):
    """(tamanho mínimo do título, tamanho do texto comum)."""
    corpo = sorted(l.tamanho for l in linhas)[len(linhas) // 2] if linhas else 11
    titulos = [l.tamanho for l in linhas if TITULO_RE.match(l.texto) and l.tamanho > corpo + 0.5]
    return ((min(titulos) - 0.1) if titulos else corpo + 0.5), corpo


def _tokens_com_x(linha):
    """Tokens da linha de acordes com a posição x inicial; parênteses ficam juntos."""
    tokens, atual, x_inicio, profundidade = [], '', None, 0
    for x0, _x1, c in linha.chars:
        if c.isspace() and profundidade == 0:
            if atual:
                tokens.append((x_inicio, atual))
            atual, x_inicio = '', None
            continue
        if not atual:
            x_inicio = x0
        atual += c
        profundidade = max(profundidade + (c == '(') - (c == ')'), 0)
    if atual:
        tokens.append((x_inicio, atual))
    return tokens


VOGAIS = set('aeiouáéíóúâêôãõàüyAEIOUÁÉÍÓÚÂÊÔÃÕÀÜY')
# encontros consonantais que ficam juntos no início da sílaba (pr, bl, ch, lh, nh...)
GRUPOS = {'pr', 'br', 'tr', 'dr', 'cr', 'gr', 'fr', 'vr', 'pl', 'bl', 'cl', 'gl', 'fl', 'tl', 'ch', 'lh', 'nh', 'qu', 'gu'}


def _inicio_da_silaba(texto, k):
    """Ajusta o índice para o começo da sílaba (no caderno o acorde fica sobre a vogal)."""
    if k >= len(texto) or not texto[k].isalpha():
        return k
    inicio_palavra = k
    while inicio_palavra > 0 and texto[inicio_palavra - 1].isalpha():
        inicio_palavra -= 1
    if k - inicio_palavra <= 1:
        return inicio_palavra  # nas duas primeiras letras: começo da palavra
    if texto[k] in VOGAIS:
        # volta sobre as consoantes que abrem a sílaba: "lou-VA-do", "can-ÇÃO", "glo-RI-a"
        j = k
        while j > inicio_palavra and texto[j - 1] not in VOGAIS:
            j -= 1
        consoantes = texto[j:k]
        if len(consoantes) >= 2 and consoantes[-2:].lower() not in GRUPOS:
            j = k - 1  # "can-ção": o 'n' fica na sílaba anterior
        elif len(consoantes) >= 2:
            j = k - 2
        return j
    # caiu numa consoante: se a próxima também for consoante (fim de sílaba), avança
    if k + 1 < len(texto) and texto[k + 1].isalpha() and texto[k + 1] not in VOGAIS \
            and texto[k:k + 2].lower() not in GRUPOS:
        return k + 1
    return k


def _juntar_por_posicao(linha_acordes, linha_letra):
    """Encaixa cada acorde no início da sílaba que está logo abaixo dele."""
    letra = linha_letra.chars
    texto = ''.join(c for _, _, c in letra)
    fim = len(texto.rstrip())

    dentro, depois = [], []
    for x, token in _tokens_com_x(linha_acordes):
        indice = next((i for i, (x0, x1, _c) in enumerate(letra[:fim]) if x < x1 - 0.5), None)
        if indice is None:
            depois.append(token)  # acorde depois do fim da letra
            continue
        while indice < fim and texto[indice].isspace():
            indice += 1  # acorde sobre um espaço: vai para a palavra seguinte
        dentro.append((_inicio_da_silaba(texto, indice), token))

    resultado = texto[:fim]
    for indice, token in reversed(dentro):
        resultado = resultado[:indice] + f'[{token}]' + resultado[indice:]
    if depois:
        resultado += ' ' + ' '.join(f'[{t}]' for t in depois)
    return resultado.strip()


def _so_acordes(linha):
    return ' '.join(f'[{t}]' for _, t in _tokens_com_x(linha))


def _converter(musica, corpo):
    """Monta o ChordPro da música a partir das linhas do PDF."""
    saida = []
    no_refrao = False
    linhas = musica.linhas
    anterior = None
    i = 0

    def abrir_refrao():
        nonlocal no_refrao
        if not no_refrao:
            while saida and saida[-1] == '':
                saida.pop()
            if saida:
                saida.append('')
            saida.append('{start_of_chorus}')
            no_refrao = True

    def fechar_refrao():
        nonlocal no_refrao
        if no_refrao:
            while saida and saida[-1] == '':
                saida.pop()
            saida.extend(['{end_of_chorus}', ''])
            no_refrao = False

    def mesma_coluna(a, b):
        return a is not None and b is not None and (a.pagina, a.coluna) == (b.pagina, b.coluna)

    while i < len(linhas):
        linha = linhas[i]
        texto = linha.texto.rstrip()
        limpo = re.sub(r'\s+', ' ', texto).strip()

        # Espaço vertical maior = novo bloco (só dentro da mesma coluna)
        if mesma_coluna(anterior, linha) and linha.rect.y0 - anterior.rect.y1 > max(linha.tamanho, corpo) * 0.6:
            if saida and saida[-1] != '':
                saida.append('')

        if linha.tamanho < corpo * 0.8:
            musica.avisos.append(f'Texto pequeno (sobrescrito?) ignorado: "{limpo}"')
            anterior = linha
            i += 1
            continue

        tom = TOM_RE.match(limpo)
        if tom:
            musica.tom = musica.tom or tom.group(1)
            anterior = linha
            i += 1
            continue

        if eh_linha_de_acordes(texto):
            proxima = linhas[i + 1] if i + 1 < len(linhas) else None
            colada = mesma_coluna(linha, proxima) and \
                proxima.rect.y0 - linha.rect.y1 < max(linha.tamanho, corpo) * 0.8
            if colada and proxima.tamanho >= corpo * 0.8 and not eh_linha_de_acordes(proxima.texto) \
                    and not eh_rotulo(proxima.texto.strip()) and not TOM_RE.match(proxima.texto):
                abrir_refrao() if proxima.italico else fechar_refrao()
                saida.append(_juntar_por_posicao(linha, proxima))
                anterior = proxima
                i += 2
                continue
            saida.append(_so_acordes(linha))
            anterior = linha
            i += 1
            continue

        if eh_rotulo(limpo) or (limpo.startswith('(') and limpo.endswith(')')):
            fechar_refrao()
            saida.append(f'{{comment: {limpo.strip("[]")}}}')
        elif linha.negrito and not linha.italico and not re.search(r'[a-zà-ú]{4,}', limpo):
            # Linha em negrito que não é acorde nem rótulo conhecido (ex.: "(*) Riff: D#--E")
            musica.avisos.append(f'Anotação mantida como comentário: "{limpo}"')
            saida.append(f'{{comment: {limpo}}}')
        else:
            abrir_refrao() if linha.italico else fechar_refrao()
            saida.append(texto.strip())
        anterior = linha
        i += 1

    fechar_refrao()
    musica.chordpro = re.sub(r'\n{3,}', '\n\n', '\n'.join(saida).strip('\n'))


def analisar_pdf(dados):
    """Recebe os bytes do PDF e devolve a lista de MusicaPDF já convertidas para ChordPro."""
    doc = fitz.open(stream=dados, filetype='pdf')
    try:
        linhas = _ler_linhas(doc)
    finally:
        doc.close()
    minimo_titulo, corpo = _tamanhos(linhas)

    musicas = []
    atual = None
    for linha in linhas:
        titulo = TITULO_RE.match(linha.texto)
        if titulo and linha.tamanho >= minimo_titulo:
            atual = MusicaPDF(numero=int(titulo.group(1)), titulo=titulo.group(2).strip())
            musicas.append(atual)
        elif atual is not None:
            atual.linhas.append(linha)

    for musica in musicas:
        _converter(musica, corpo)
        musica.tom = re.sub(r'\s+', ' ', musica.tom).strip()[:10]
        if not musica.tom:
            musica.avisos.append('Tom não informado no PDF')
        musica.linhas = []
    return musicas
