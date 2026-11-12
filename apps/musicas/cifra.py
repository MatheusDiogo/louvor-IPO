"""Cifras no formato ChordPro: leitura, transposição, HTML e conversão de "cifra comum".

Subconjunto suportado do ChordPro:
  [G]letra            acorde na posição exata da sílaba
  {title: ...}  {t:}  título (usado só na importação/edição)
  {key: ...}    {k:}  tom original
  {comment: ...} {c:} {ci:} {cb:}   anotação (ex.: "Intro: E A9 B"); acordes nela também são transpostos.
                      Pode ficar sozinha na linha ou junto com letra/acordes ("Santo [A]santo {c: 2x}").
  {start_of_chorus} / {soc} ... {end_of_chorus} / {eoc}   refrão
  {start_of_verse} / {sov} ... {eov},  {start_of_bridge} / {sob} ... {eob}
  {chorus}            repete o refrão (mostra "Refrão")
  # linha            comentário interno (não é exibido)
"""
import re
from dataclasses import dataclass, field

from django.utils.html import escape

# ------------------------------------------------------------------ acordes

NOTAS_SUSTENIDO = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTAS_BEMOL = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
INDICE_NOTA = {n: i for i, n in enumerate(NOTAS_SUSTENIDO)}
INDICE_NOTA.update({n: i for i, n in enumerate(NOTAS_BEMOL)})
INDICE_NOTA.update({'Cb': 11, 'B#': 0, 'E#': 5, 'Fb': 4})

# Tons em que se escreve com bemóis
TONS_BEMOL = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm'}

# Tons oferecidos para escolha (nomes mais usados)
TONS_MAIORES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
TONS_MENORES = ['Cm', 'C#m', 'Dm', 'Ebm', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'Bbm', 'Bm']

ACORDE_RE = re.compile(
    r'^(?P<raiz>[A-G][#b]?)'
    r'(?P<sufixo>(?:[^/\s]|/(?=[0-9(]))*)'
    r'(?:/(?P<baixo>[A-G][#b]?))?$'
)
SUFIXO_VALIDO_RE = re.compile(r'^(?:maj|min|dim|aug|sus|add|m|M|[0-9]|[°º+\-#b()/x]|ø)*$')
# Pedaços de texto que podem ser acordes dentro de anotações: "(A/B – início)", "D—C—G/B"
TOKEN_RE = re.compile(r"[^\s()\[\]{},;:—–|]+")


def eh_acorde(token):
    m = ACORDE_RE.match(token or '')
    return bool(m and SUFIXO_VALIDO_RE.match(m.group('sufixo')))


def _nota(nome, semitons, bemol):
    if nome not in INDICE_NOTA:
        return nome
    tabela = NOTAS_BEMOL if bemol else NOTAS_SUSTENIDO
    return tabela[(INDICE_NOTA[nome] + semitons) % 12]


def transpor_acorde(acorde, semitons, bemol=False):
    if not semitons and not bemol:
        return acorde
    m = ACORDE_RE.match(acorde)
    if not m or not SUFIXO_VALIDO_RE.match(m.group('sufixo')):
        return acorde
    resultado = _nota(m.group('raiz'), semitons, bemol) + m.group('sufixo')
    if m.group('baixo'):
        resultado += '/' + _nota(m.group('baixo'), semitons, bemol)
    return resultado


def transpor_texto(texto, semitons, bemol=False, marcar=None):
    """Transpõe os acordes que aparecem num texto livre (anotação, sequência "D—C—G/B").

    `marcar`, se informado, recebe o acorde já transposto e devolve o texto a inserir
    (usado para destacar os acordes no HTML). O resto do texto é escapado.
    """
    partes = []
    ultimo = 0
    for m in TOKEN_RE.finditer(texto):
        antes = texto[ultimo:m.start()]
        partes.append(escape(antes) if marcar else antes)
        token = m.group(0)
        if eh_acorde(token):
            novo = transpor_acorde(token, semitons, bemol)
            partes.append(marcar(novo) if marcar else novo)
        else:
            partes.append(escape(token) if marcar else token)
        ultimo = m.end()
    resto = texto[ultimo:]
    partes.append(escape(resto) if marcar else resto)
    return ''.join(partes)


def tom_base(tom):
    """'Dm (F)' -> 'Dm';  'C#m7' -> 'C#m';  '' -> ''."""
    m = re.match(r'\s*([A-G][#b]?)(m(?!aj))?', tom or '')
    if not m:
        return ''
    return m.group(1) + ('m' if m.group(2) else '')


def eh_menor(tom):
    return tom_base(tom).endswith('m')


def semitons_entre(tom_original, tom_destino):
    a, b = tom_base(tom_original), tom_base(tom_destino)
    if not a or not b:
        return 0
    return (INDICE_NOTA[b.rstrip('m')] - INDICE_NOTA[a.rstrip('m')]) % 12


def usa_bemol(tom):
    return tom_base(tom) in TONS_BEMOL


def opcoes_de_tom(tom_original):
    """Lista de tons para escolher (maiores ou menores, conforme o tom original)."""
    if not tom_base(tom_original):
        return TONS_MAIORES + TONS_MENORES
    return TONS_MENORES if eh_menor(tom_original) else TONS_MAIORES


def normalizar_tom(tom):
    """Escreve o tom do jeito da lista de opções (ex.: 'A#' -> 'Bb', 'Dbm' -> 'C#m')."""
    base = tom_base(tom)
    if not base:
        return (tom or '').strip()
    menor = base.endswith('m')
    indice = INDICE_NOTA[base.rstrip('m')]
    return (TONS_MENORES if menor else TONS_MAIORES)[indice]


# ------------------------------------------------------------------ leitura do ChordPro

DIRETIVA_RE = re.compile(r'^\s*\{\s*([A-Za-z_]+)\s*(?::\s*(.*?))?\s*\}\s*$')
ALIASES = {
    't': 'title', 'st': 'subtitle', 'k': 'key', 'c': 'comment', 'ci': 'comment',
    'cb': 'comment', 'comment_italic': 'comment', 'comment_box': 'comment',
    'soc': 'start_of_chorus', 'eoc': 'end_of_chorus',
    'sov': 'start_of_verse', 'eov': 'end_of_verse',
    'sob': 'start_of_bridge', 'eob': 'end_of_bridge',
}
NOMES_SECAO = {'chorus': 'Refrão', 'verse': '', 'bridge': 'Ponte'}


class Comentario(str):
    """Comentário no meio de uma linha de letra/acordes: "Santo [A]santo {c: 2x}"."""


# {comment: ...} em qualquer ponto da linha
COMENTARIO_INLINE_RE = re.compile(
    r'\{\s*(?:comment|c|ci|cb|comment_italic|comment_box)\s*:\s*([^}]*?)\s*\}',
    re.IGNORECASE,
)


def tem_acorde_no_texto(texto):
    """Há algum acorde num texto livre (comentário)?"""
    return any(eh_acorde(t) for t in TOKEN_RE.findall(texto or ''))


@dataclass
class Linha:
    tipo: str                 # 'letra' | 'comentario' | 'vazia' | 'inicio' | 'fim' | 'refrao'
    partes: list = field(default_factory=list)   # [(acorde, letra ou Comentario), ...] para 'letra'
    texto: str = ''           # comentário / rótulo de seção
    secao: str = ''           # 'chorus' | 'verse' | 'bridge' (para 'inicio'/'fim')


@dataclass
class Cifra:
    titulo: str = ''
    tom: str = ''
    linhas: list = field(default_factory=list)


def ler_chordpro(texto):
    cifra = Cifra()
    for bruta in (texto or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        linha = bruta.rstrip()
        if linha.lstrip().startswith('#'):
            continue
        diretiva = DIRETIVA_RE.match(linha)
        if diretiva:
            nome = ALIASES.get(diretiva.group(1).lower(), diretiva.group(1).lower())
            valor = (diretiva.group(2) or '').strip()
            if nome == 'title':
                cifra.titulo = valor
            elif nome == 'key':
                cifra.tom = valor
            elif nome == 'comment':
                cifra.linhas.append(Linha('comentario', texto=valor))
            elif nome.startswith('start_of_'):
                secao = nome[len('start_of_'):]
                cifra.linhas.append(Linha('inicio', secao=secao, texto=valor or NOMES_SECAO.get(secao, '')))
            elif nome.startswith('end_of_'):
                cifra.linhas.append(Linha('fim', secao=nome[len('end_of_'):]))
            elif nome == 'chorus':
                cifra.linhas.append(Linha('refrao', texto=valor or 'Refrão'))
            continue
        if not linha.strip():
            cifra.linhas.append(Linha('vazia'))
            continue
        # Comentários no meio da linha continuam sendo comentários; o resto é letra com acordes
        partes = []
        trechos = COMENTARIO_INLINE_RE.split(linha)
        for indice, trecho in enumerate(trechos):
            if indice % 2:
                partes.append(('', Comentario(trecho)))
                continue
            pedacos = re.split(r'\[([^\]]*)\]', trecho)
            if pedacos[0]:
                partes.append(('', pedacos[0]))
            for i in range(1, len(pedacos), 2):
                partes.append((pedacos[i].strip(), pedacos[i + 1]))
        cifra.linhas.append(Linha('letra', partes=partes))
    return cifra


def acordes_usados(texto, tom_original='', tom_destino=''):
    """Acordes da música (sem repetir, na ordem em que aparecem), já no tom de destino.

    Inclui os acordes escritos nas anotações ("Intro: E A9 B").
    """
    cifra = ler_chordpro(texto)
    tom_original = tom_original or cifra.tom
    semitons = semitons_entre(tom_original, tom_destino) if tom_destino else 0
    bemol = usa_bemol(tom_destino or tom_original)
    transpor = bool(semitons) or (tom_destino and tom_base(tom_destino) != tom_base(tom_original))

    textos = []
    for linha in cifra.linhas:
        if linha.tipo == 'comentario':
            textos.append(linha.texto)
        elif linha.tipo == 'letra':
            textos.extend(a for a, _ in linha.partes if a)
            textos.extend(l for _, l in linha.partes if isinstance(l, Comentario))
    vistos = []
    for texto_acordes in textos:
        for token in TOKEN_RE.findall(texto_acordes):
            if eh_acorde(token):
                nome = transpor_acorde(token, semitons, bemol) if transpor else token
                if nome not in vistos:
                    vistos.append(nome)
    return vistos


def letra_para_busca(texto, limite=4000):
    """Só a letra da música (sem acordes, diretivas e comentários), numa linha, para buscas."""
    partes = []
    for linha in (texto or '').splitlines():
        if DIRETIVA_RE.match(linha) or linha.lstrip().startswith('#'):
            continue
        letra = re.sub(r'\[[^\]]*\]', '', COMENTARIO_INLINE_RE.sub(' ', linha)).strip()
        if letra:
            partes.append(letra)
    return re.sub(r'\s+', ' ', ' '.join(partes))[:limite]


def extrair_metadados(texto):
    """Tira {title} e {key} do texto (eles viram campos da música). Devolve (texto, titulo, tom)."""
    titulo = tom = ''
    restantes = []
    for linha in (texto or '').replace('\r\n', '\n').split('\n'):
        d = DIRETIVA_RE.match(linha)
        if d and ALIASES.get(d.group(1).lower(), d.group(1).lower()) in ('title', 'key'):
            if ALIASES.get(d.group(1).lower(), d.group(1).lower()) == 'title':
                titulo = titulo or (d.group(2) or '').strip()
            else:
                tom = tom or (d.group(2) or '').strip()
            continue
        restantes.append(linha)
    return '\n'.join(restantes).strip('\n'), titulo, tom


# ------------------------------------------------------------------ HTML

def _acorde_html(acorde):
    return f'<span class="cp-chord-inline">{escape(acorde)}</span>'


def renderizar_html(texto, tom_original='', tom_destino=''):
    """HTML da cifra (classes cp-*), já transposta para `tom_destino` se informado."""
    cifra = ler_chordpro(texto)
    tom_original = tom_original or cifra.tom
    semitons = semitons_entre(tom_original, tom_destino) if tom_destino else 0
    bemol = usa_bemol(tom_destino or tom_original)
    transpor = bool(semitons) or (tom_destino and tom_base(tom_destino) != tom_base(tom_original))

    def comentario_html(texto, tag='span', classe='cp-comment-inline'):
        """Comentário com os acordes transpostos. Se tiver acorde, some no modo "sem acordes"."""
        conteudo = transpor_texto(texto, semitons, bemol if transpor else False, marcar=_acorde_html)
        if tem_acorde_no_texto(texto):
            classe += ' cp-com-acorde'
        return f'<{tag} class="{classe}">{conteudo}</{tag}>'

    html = ['<div class="cp-song">']
    vazias = 0
    for linha in cifra.linhas:
        if linha.tipo == 'vazia':
            vazias += 1
            if vazias == 1:
                html.append('<div class="cp-space"></div>')
            continue
        vazias = 0
        if linha.tipo == 'comentario':
            html.append(comentario_html(linha.texto, 'div', 'cp-comment'))
        elif linha.tipo == 'inicio':
            html.append(f'<div class="cp-section cp-{escape(linha.secao)}">')
            if linha.texto:
                html.append(f'<div class="cp-label">{escape(linha.texto)}</div>')
        elif linha.tipo == 'fim':
            html.append('</div>')
        elif linha.tipo == 'refrao':
            html.append(f'<div class="cp-label cp-chorus-ref">{escape(linha.texto)}</div>')
        else:
            tem_acorde = any(a for a, _ in linha.partes)
            if not tem_acorde:
                letra = ''.join(
                    comentario_html(l) if isinstance(l, Comentario) else escape(l) for _, l in linha.partes
                )
                html.append(f'<div class="cp-line cp-lyrics-only"><span class="cp-lyric">{letra}</span></div>')
                continue
            so_acordes = not ''.join(l for _, l in linha.partes if not isinstance(l, Comentario)).strip()
            classe = 'cp-line cp-chords-only' if so_acordes else 'cp-line'
            html.append(f'<div class="{classe}">')
            for acorde, letra in linha.partes:
                if isinstance(letra, Comentario):
                    # Numa linha só de acordes o comentário fica na altura dos acordes; senão, na da letra
                    comentario = comentario_html(letra)
                    # (o espaço embaixo deixa o bloco da mesma altura dos acordes, que também têm um espaço)
                    topo, baixo = (comentario, ' ') if so_acordes else ('', comentario + ' ')
                    html.append(f'<span class="cp-chunk"><span class="cp-chord">{topo}</span>'
                                f'<span class="cp-lyric">{baixo}</span></span>')
                    continue
                acorde_t = transpor_texto(acorde, semitons, bemol if transpor else False) if acorde else ''
                # Cada palavra vira um bloco: no celular a linha quebra entre palavras
                palavras = re.findall(r'\S+\s*|\s+', letra) or ['']
                for indice, palavra in enumerate(palavras):
                    html.append(
                        '<span class="cp-chunk">'
                        f'<span class="cp-chord">{escape(acorde_t) if indice == 0 else ""}</span>'
                        f'<span class="cp-lyric">{escape(palavra)}</span>'
                        '</span>'
                    )
            html.append('</div>')
    # fecha seções sem {end_of_...}
    abertas = sum(1 for l in cifra.linhas if l.tipo == 'inicio') - sum(1 for l in cifra.linhas if l.tipo == 'fim')
    html.extend(['</div>'] * max(abertas, 0))
    html.append('</div>')
    return ''.join(html)


# ------------------------------------------------------------------ "cifra comum" -> ChordPro

ROTULO_RE = re.compile(
    r'^\s*(?P<abre>[\[(])?\s*(?:intro(?:dução)?|final|fim|interl[uú]dio|solo|riff|ponte|pr[ée][- ]?refr[aã]o|'
    r'refr[aã]o|coro|verso|estrofe|parte|tag|outro|ending|chorus|bridge|verse)\b\s*\d*\s*'
    r'(?P<fecha>[:\])])?\s*(?P<resto>.*)$',
    re.IGNORECASE,
)
SEPARADORES_RE = re.compile(r'[—–]+|-{2,}')


def eh_rotulo(linha):
    """"Intro: E A9", "[Refrão]", "Final:", "Ponte" — mas não uma letra como "Coro celestial"."""
    m = ROTULO_RE.match(linha or '')
    if not m:
        return False
    if m.group('abre') or m.group('fecha'):
        return True
    resto = m.group('resto').strip()
    return not resto or eh_linha_de_acordes(resto)


def tem_acorde_chordpro(texto):
    return any(eh_acorde(c.strip()) for c in re.findall(r'\[([^\]\n]*)\]', texto or ''))


def _tokens_da_linha(linha):
    """Tokens com posição; parênteses são mantidos juntos: "(A/B – início)"."""
    return [(m.start(), m.group(0)) for m in re.finditer(r'\([^)]*\)?|\[[^\]]*\]?|\S+', linha)]


def eh_linha_de_acordes(linha):
    tokens = [t for _, t in _tokens_da_linha(linha)]
    if not tokens:
        return False
    acordes = 0
    for token in tokens:
        if token[0] in '([':
            continue  # anotação entre parênteses é aceita numa linha de acordes
        pedacos = [p for p in SEPARADORES_RE.split(token) if p]
        if not pedacos:
            continue  # só traço
        for p in pedacos:
            if eh_acorde(p):
                acordes += 1
            elif not re.fullmatch(r'(?i)\d+x|x\d+|%|\|+|\.+', p):
                return False
    return acordes > 0


def _juntar(linha_acordes, linha_letra):
    letra = linha_letra.rstrip()
    tokens = _tokens_da_linha(linha_acordes)
    if tokens and tokens[-1][0] > len(letra):
        letra = letra.ljust(tokens[-1][0])
    for posicao, token in reversed(tokens):
        posicao = min(posicao, len(letra))
        letra = letra[:posicao] + f'[{token}]' + letra[posicao:]
    return letra


def _so_acordes(linha_acordes):
    return ' '.join(f'[{t}]' for _, t in _tokens_da_linha(linha_acordes))


def converter_cifra_comum(texto):
    """Converte "acordes em cima da letra" (Cifra Club, Word...) para ChordPro.

    Devolve (chordpro, titulo, tom). Linhas já em ChordPro são mantidas.
    """
    linhas = (texto or '').replace('\t', '    ').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    saida = []
    titulo = tom = ''
    i = 0
    while i < len(linhas):
        linha = linhas[i].rstrip()
        bruta = linha.strip()

        if DIRETIVA_RE.match(linha) or tem_acorde_chordpro(linha):
            saida.append(linha)  # já está em ChordPro
            i += 1
            continue

        tom_m = re.match(r'^\s*tom\s*:\s*(.*?)\s*$', linha, re.IGNORECASE)
        if tom_m:
            tom = tom or tom_m.group(1)
            i += 1
            continue

        if eh_linha_de_acordes(linha):
            proxima = linhas[i + 1].rstrip() if i + 1 < len(linhas) else ''
            if proxima.strip() and not eh_linha_de_acordes(proxima) and not DIRETIVA_RE.match(proxima) \
                    and not eh_rotulo(proxima):
                saida.append(_juntar(linha, proxima))
                i += 2
            else:
                saida.append(_so_acordes(linha))
                i += 1
            continue

        if eh_rotulo(linha):
            rotulo = bruta.strip('[]')
            saida.append(f'{{comment: {rotulo}}}')
            i += 1
            continue

        saida.append(linha)
        i += 1

    # Remove linhas vazias repetidas no começo/fim
    resultado = '\n'.join(saida).strip('\n')
    resultado = re.sub(r'\n{3,}', '\n\n', resultado)
    return resultado, titulo, tom


def parece_chordpro(texto):
    return tem_acorde_chordpro(texto) or any(DIRETIVA_RE.match(l) for l in (texto or '').splitlines())
