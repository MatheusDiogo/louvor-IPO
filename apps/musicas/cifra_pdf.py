"""Gera PDF de cifras (ChordPro) já transpostas: acorde em cima, letra embaixo."""
import re

import fitz  # PyMuPDF

from .cifra import Comentario, ler_chordpro, semitons_entre, tom_base, transpor_texto, usa_bemol

LARGURA, ALTURA = fitz.paper_size('a4')
MARGEM = 42
VERDE = (0.086, 0.396, 0.204)
CINZA = (0.42, 0.45, 0.48)
PRETO = (0.1, 0.12, 0.1)

TAM_TITULO, TAM_INFO, TAM_ACORDE, TAM_LETRA, TAM_COMENTARIO = 17, 10, 10, 11.5, 10

TROCAS = {'→': '->', '—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...', '•': '-', ' ': ' '}


def _limpar(texto):
    """As fontes internas do PDF não têm alguns símbolos (travessão, aspas curvas...)."""
    for de, para in TROCAS.items():
        texto = texto.replace(de, para)
    return texto


_FONTES = {}


def _largura(texto, fonte, tamanho):
    # fitz.get_text_length subestima letras acentuadas; Font.text_length mede corretamente
    if fonte not in _FONTES:
        _FONTES[fonte] = fitz.Font(fonte)
    return _FONTES[fonte].text_length(_limpar(texto), fontsize=tamanho)


ESPACO_COLUNAS = 24


class _Escritor:
    """Escreve de cima para baixo; com 2 colunas, ao encher a da esquerda continua na da direita."""

    def __init__(self, doc):
        self.doc = doc
        self.pagina = None
        self.y = 0
        self.colunas = 1
        self.coluna = 0
        self.topo_colunas = MARGEM  # onde as colunas começam (abaixo do título, na 1ª página da música)

    @property
    def largura_coluna(self):
        return (LARGURA - 2 * MARGEM - (self.colunas - 1) * ESPACO_COLUNAS) / self.colunas

    @property
    def x0(self):
        return MARGEM + self.coluna * (self.largura_coluna + ESPACO_COLUNAS)

    @property
    def limite(self):
        return self.x0 + self.largura_coluna

    def nova_pagina(self):
        self.pagina = self.doc.new_page(width=LARGURA, height=ALTURA)
        self.y = MARGEM
        self.coluna = 0
        self.topo_colunas = MARGEM

    def iniciar_colunas(self, colunas):
        self.colunas, self.coluna, self.topo_colunas = colunas, 0, self.y

    def garantir(self, altura):
        if self.pagina is None:
            self.nova_pagina()
        elif self.y + altura > ALTURA - MARGEM:
            if self.coluna + 1 < self.colunas:
                self.coluna += 1
                self.y = self.topo_colunas
                # linha fina separando as colunas
                x = self.x0 - ESPACO_COLUNAS / 2
                self.pagina.draw_line((x, self.topo_colunas), (x, ALTURA - MARGEM), color=(0.85, 0.87, 0.86), width=0.6)
            else:
                self.nova_pagina()

    def texto(self, x, y, texto, fonte, tamanho, cor=PRETO):
        self.pagina.insert_text((x, y), _limpar(texto), fontname=fonte, fontsize=tamanho, color=cor)


def _pedacos(partes):
    """Divide cada trecho de letra em palavras para permitir quebra de linha."""
    resultado = []
    for acorde, letra in partes:
        if isinstance(letra, Comentario):
            resultado.append((acorde, letra))  # comentário no meio da linha não é dividido
            continue
        palavras = re.findall(r'\S+\s*|\s+', letra) or ['']
        resultado.append((acorde, palavras[0]))
        resultado.extend(('', p) for p in palavras[1:])
    return resultado


def _escrever_linha(esc, partes, transpor, recuo, italico):
    fonte_letra = 'heit' if italico else 'helv'
    tem_acorde = any(a for a, _ in partes)
    so_acordes = tem_acorde and not ''.join(l for _, l in partes if not isinstance(l, Comentario)).strip()
    altura_acorde = TAM_ACORDE + 2 if tem_acorde else 0
    altura_letra = 0 if so_acordes else TAM_LETRA + 3
    largura_disponivel = esc.largura_coluna   # posições relativas ao início da coluna

    linha = []
    x = recuo

    def descarregar():
        nonlocal linha, x
        if not linha:
            return
        esc.garantir(altura_acorde + altura_letra + 2)  # pode passar para a outra coluna/página
        for px, topo, baixo, comentario in linha:
            if topo:
                fonte, tamanho, cor = ('heit', TAM_COMENTARIO, CINZA) if comentario else ('hebo', TAM_ACORDE, VERDE)
                esc.texto(esc.x0 + px, esc.y + TAM_ACORDE, topo, fonte, tamanho, cor)
            if baixo.strip():
                fonte, tamanho, cor = ('heit', TAM_COMENTARIO, CINZA) if comentario else (fonte_letra, TAM_LETRA, PRETO)
                esc.texto(esc.x0 + px, esc.y + altura_acorde + TAM_LETRA, baixo, fonte, tamanho, cor)
        esc.y += altura_acorde + altura_letra + 2
        linha, x = [], recuo + 10  # continuação levemente recuada

    for acorde, letra in _pedacos(partes):
        comentario = isinstance(letra, Comentario)
        if comentario:
            # Comentário em itálico cinza: na altura dos acordes numa linha só de acordes, senão na da letra
            texto = transpor(letra) + ' '
            topo, baixo = (texto, '') if so_acordes else ('', texto)
            largura = _largura(texto, 'heit', TAM_COMENTARIO) + 4
        else:
            topo, baixo = (transpor(acorde) if acorde else ''), letra
            largura_acorde = _largura(topo, 'hebo', TAM_ACORDE) + 4 if topo else 0
            largura = max(largura_acorde, _largura(baixo, fonte_letra, TAM_LETRA))
        if x + largura > largura_disponivel and linha:
            descarregar()
        linha.append((x, topo, baixo, comentario))
        x += largura
    descarregar()


def _quebrar(texto, fonte, tamanho, largura):
    """Quebra o texto em linhas que cabem na largura (respeitando as quebras que a pessoa digitou)."""
    linhas = []
    for paragrafo in texto.splitlines() or ['']:
        atual = ''
        for palavra in paragrafo.split():
            tentativa = f'{atual} {palavra}'.strip()
            if atual and _largura(tentativa, fonte, tamanho) > largura:
                linhas.append(atual)
                atual = palavra
            else:
                atual = tentativa
        linhas.append(atual)
    return linhas


def _escrever_anotacoes(esc, anotacoes):
    """Caixa amarela com as anotações do culto (começo, arranjo, final), abaixo do título."""
    tamanho, entre = TAM_COMENTARIO, TAM_COMENTARIO + 3
    largura_rotulo = max(_largura(rotulo.upper(), 'hebo', tamanho - 1) for rotulo, _ in anotacoes) + 10
    largura_texto = LARGURA - 2 * MARGEM - 20 - largura_rotulo
    blocos = [(rotulo, _quebrar(texto, 'helv', tamanho, largura_texto)) for rotulo, texto in anotacoes]
    altura = sum(len(linhas) for _, linhas in blocos) * entre + (len(blocos) - 1) * 3 + 12
    esc.garantir(altura + 8)
    caixa = fitz.Rect(MARGEM, esc.y, LARGURA - MARGEM, esc.y + altura)
    esc.pagina.draw_rect(caixa, color=(0.99, 0.90, 0.54), fill=(1, 0.98, 0.92), width=0.8)
    y = esc.y + 6
    for rotulo, linhas in blocos:
        esc.texto(MARGEM + 10, y + tamanho, rotulo.upper(), 'hebo', tamanho - 1, (0.57, 0.25, 0.05))
        for linha in linhas:
            esc.texto(MARGEM + 10 + largura_rotulo, y + tamanho, linha, 'helv', tamanho, PRETO)
            y += entre
        y += 3
    esc.y += altura + 12


def _escrever_musica(esc, nome, cifra_texto, tom_original, tom_destino, subtitulo='', colunas=1, anotacoes=None):
    cifra = ler_chordpro(cifra_texto)
    tom_original = tom_original or cifra.tom
    tom_final = tom_destino or tom_original
    semitons = semitons_entre(tom_original, tom_destino) if tom_destino else 0
    bemol = usa_bemol(tom_final)
    mudou = tom_destino and tom_base(tom_destino) != tom_base(tom_original)

    def transpor(texto):
        return transpor_texto(texto, semitons, bemol) if mudou else texto

    esc.iniciar_colunas(1)  # título e tom ocupam a largura toda
    esc.garantir(TAM_TITULO + 30)
    esc.texto(MARGEM, esc.y + TAM_TITULO, nome, 'hebo', TAM_TITULO, VERDE)
    esc.y += TAM_TITULO + 6
    info = ' · '.join(p for p in [subtitulo, f'Tom: {tom_final}' if tom_final else ''] if p)
    if info:
        esc.texto(MARGEM, esc.y + TAM_INFO, info.replace('·', '-'), 'hebo', TAM_INFO, CINZA)
        esc.y += TAM_INFO + 10
    if anotacoes:
        _escrever_anotacoes(esc, anotacoes)
    esc.iniciar_colunas(colunas)

    secoes = []
    vazias = 0
    for linha in cifra.linhas:
        recuo = 14 if 'chorus' in secoes else 0
        italico = 'chorus' in secoes
        if linha.tipo == 'vazia':
            vazias += 1
            if vazias == 1:
                esc.y += 8
            continue
        vazias = 0
        if linha.tipo == 'inicio':
            secoes.append(linha.secao)
            if linha.texto:
                esc.garantir(TAM_INFO + 4)
                esc.texto(esc.x0, esc.y + TAM_INFO, linha.texto.upper(), 'hebo', TAM_INFO - 1, CINZA)
                esc.y += TAM_INFO + 3
        elif linha.tipo == 'fim':
            if secoes:
                secoes.pop()
        elif linha.tipo == 'refrao':
            esc.garantir(TAM_INFO + 4)
            esc.texto(esc.x0, esc.y + TAM_INFO, f'({linha.texto})', 'hebi', TAM_INFO, CINZA)
            esc.y += TAM_INFO + 4
        elif linha.tipo == 'comentario':
            esc.garantir(TAM_COMENTARIO + 4)
            esc.texto(esc.x0 + recuo, esc.y + TAM_COMENTARIO, transpor(linha.texto), 'hebi', TAM_COMENTARIO, CINZA)
            esc.y += TAM_COMENTARIO + 5
        else:
            _escrever_linha(esc, linha.partes, transpor, recuo, italico)


def _paginas_em_uma_coluna(item):
    """Quantas páginas a música ocupa numa coluna só (desenhada num rascunho, que é descartado)."""
    rascunho = fitz.open()
    try:
        esc = _Escritor(rascunho)
        esc.nova_pagina()
        _escrever_musica(esc, item['nome'], item.get('cifra', ''), item.get('tom_original', ''),
                         item.get('tom', ''), item.get('subtitulo', ''), anotacoes=item.get('anotacoes'))
        return len(rascunho)
    finally:
        rascunho.close()


def gerar_pdf(musicas, titulo_documento=''):
    """`musicas`: lista de dicts {nome, cifra, tom_original, tom, subtitulo, anotacoes}. Cada música começa numa
    página. `anotacoes` (opcional): [(rótulo, texto), ...] do culto, numa caixa abaixo do título.

    A música que não cabe numa página sai em duas colunas.
    """
    doc = fitz.open()
    esc = _Escritor(doc)
    for item in musicas:
        colunas = 2 if _paginas_em_uma_coluna(item) > 1 else 1
        esc.nova_pagina()
        _escrever_musica(esc, item['nome'], item.get('cifra', ''), item.get('tom_original', ''),
                         item.get('tom', ''), item.get('subtitulo', ''), colunas=colunas,
                         anotacoes=item.get('anotacoes'))
    if not musicas:
        esc.iniciar_colunas(1)
        esc.nova_pagina()
        esc.texto(MARGEM, MARGEM + 20, 'Nenhuma música.', 'helv', 12)
    total = len(doc)
    for numero, pagina in enumerate(doc, start=1):
        rodape = f'{titulo_documento} - {numero}/{total}' if titulo_documento else f'{numero}/{total}'
        pagina.insert_text((MARGEM, ALTURA - 20), _limpar(rodape), fontname='helv', fontsize=8, color=CINZA)
    doc.set_metadata({'title': titulo_documento or (musicas[0]['nome'] if musicas else 'Cifras'),
                      'creator': 'Louvor IPO'})
    dados = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return dados
