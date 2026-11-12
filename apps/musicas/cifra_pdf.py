"""Gera PDF de cifras (ChordPro) já transpostas: acorde em cima, letra embaixo."""
import re

import fitz  # PyMuPDF

from .cifra import Anotacao, ler_chordpro, semitons_entre, tom_base, transpor_texto, usa_bemol

LARGURA, ALTURA = fitz.paper_size('a4')
MARGEM = 42
VERDE = (0.086, 0.396, 0.204)
CINZA = (0.42, 0.45, 0.48)
PRETO = (0.1, 0.12, 0.1)

TAM_TITULO, TAM_INFO, TAM_ACORDE, TAM_LETRA, TAM_COMENTARIO = 17, 10, 10, 11.5, 10

TROCAS = {'—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...', '•': '-', ' ': ' '}


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


class _Escritor:
    def __init__(self, doc):
        self.doc = doc
        self.pagina = None
        self.y = 0

    def nova_pagina(self):
        self.pagina = self.doc.new_page(width=LARGURA, height=ALTURA)
        self.y = MARGEM

    def garantir(self, altura):
        if self.pagina is None or self.y + altura > ALTURA - MARGEM:
            self.nova_pagina()

    def texto(self, x, y, texto, fonte, tamanho, cor=PRETO):
        self.pagina.insert_text((x, y), _limpar(texto), fontname=fonte, fontsize=tamanho, color=cor)


def _pedacos(partes):
    """Divide cada trecho de letra em palavras para permitir quebra de linha."""
    resultado = []
    for acorde, letra in partes:
        palavras = re.findall(r'\S+\s*|\s+', letra) or ['']
        resultado.append((acorde, palavras[0]))
        resultado.extend(('', p) for p in palavras[1:])
    return resultado


def _escrever_linha(esc, partes, transpor, recuo, italico):
    fonte_letra = 'heit' if italico else 'helv'
    tem_acorde = any(a for a, _ in partes)
    so_acordes = not ''.join(l for _, l in partes).strip()
    altura_acorde = TAM_ACORDE + 2 if tem_acorde else 0
    altura_letra = 0 if so_acordes else TAM_LETRA + 3
    limite = LARGURA - MARGEM

    linha = []
    x = MARGEM + recuo

    def descarregar():
        nonlocal linha, x
        if not linha:
            return
        esc.garantir(altura_acorde + altura_letra + 2)
        for px, acorde, letra, fonte_topo in linha:
            if acorde:
                cor = CINZA if fonte_topo == 'heit' else VERDE
                esc.texto(px, esc.y + TAM_ACORDE, acorde, fonte_topo, TAM_ACORDE, cor)
            if letra.strip():
                esc.texto(px, esc.y + altura_acorde + TAM_LETRA, letra, fonte_letra, TAM_LETRA)
        esc.y += altura_acorde + altura_letra + 2
        linha, x = [], MARGEM + recuo + 10  # continuação levemente recuada

    for acorde, letra in _pedacos(partes):
        # Anotação em cima da letra ([{comment: ...}]) sai em itálico cinza; acorde em negrito verde
        fonte_topo = 'heit' if isinstance(acorde, Anotacao) else 'hebo'
        acorde = transpor(acorde) if acorde else ''
        largura_acorde = _largura(acorde, fonte_topo, TAM_ACORDE) + 4 if acorde else 0
        largura_letra = _largura(letra, fonte_letra, TAM_LETRA)
        largura = max(largura_acorde, largura_letra)
        if x + largura > limite and linha:
            descarregar()
        linha.append((x, acorde, letra, fonte_topo))
        x += largura
    descarregar()


def _escrever_musica(esc, nome, cifra_texto, tom_original, tom_destino, subtitulo=''):
    cifra = ler_chordpro(cifra_texto)
    tom_original = tom_original or cifra.tom
    tom_final = tom_destino or tom_original
    semitons = semitons_entre(tom_original, tom_destino) if tom_destino else 0
    bemol = usa_bemol(tom_final)
    mudou = tom_destino and tom_base(tom_destino) != tom_base(tom_original)

    def transpor(texto):
        return transpor_texto(texto, semitons, bemol) if mudou else texto

    esc.garantir(TAM_TITULO + 30)
    esc.texto(MARGEM, esc.y + TAM_TITULO, nome, 'hebo', TAM_TITULO, VERDE)
    esc.y += TAM_TITULO + 6
    info = ' · '.join(p for p in [subtitulo, f'Tom: {tom_final}' if tom_final else ''] if p)
    if info:
        esc.texto(MARGEM, esc.y + TAM_INFO, info.replace('·', '-'), 'hebo', TAM_INFO, CINZA)
        esc.y += TAM_INFO + 10

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
                esc.texto(MARGEM, esc.y + TAM_INFO, linha.texto.upper(), 'hebo', TAM_INFO - 1, CINZA)
                esc.y += TAM_INFO + 3
        elif linha.tipo == 'fim':
            if secoes:
                secoes.pop()
        elif linha.tipo == 'refrao':
            esc.garantir(TAM_INFO + 4)
            esc.texto(MARGEM, esc.y + TAM_INFO, f'({linha.texto})', 'hebi', TAM_INFO, CINZA)
            esc.y += TAM_INFO + 4
        elif linha.tipo == 'comentario':
            esc.garantir(TAM_COMENTARIO + 4)
            esc.texto(MARGEM + recuo, esc.y + TAM_COMENTARIO, transpor(linha.texto), 'hebi', TAM_COMENTARIO, CINZA)
            esc.y += TAM_COMENTARIO + 5
        else:
            _escrever_linha(esc, linha.partes, transpor, recuo, italico)


def gerar_pdf(musicas, titulo_documento=''):
    """`musicas`: lista de dicts {nome, cifra, tom_original, tom, subtitulo}. Cada música começa numa página."""
    doc = fitz.open()
    esc = _Escritor(doc)
    for item in musicas:
        esc.nova_pagina()
        _escrever_musica(esc, item['nome'], item.get('cifra', ''), item.get('tom_original', ''),
                         item.get('tom', ''), item.get('subtitulo', ''))
    if not musicas:
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
