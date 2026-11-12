"""Desenhos de acordes (diagramas) para o violão.

De onde vem cada desenho, nesta ordem de preferência:
  1. tabela DesenhoAcorde, origem "equipe" (cadastrados por nós);
  2. tabela DesenhoAcorde, origem "base" (importados da chords-db, licença MIT);
  3. acorde com baixo diferente (B/D#) que não está na tabela: gerado a partir do acorde sem o baixo,
     colocando a nota do baixo na corda mais grave (como o violonista faz na prática).

O nome escrito na cifra ("A4", "C7M", "Bm7(b5)") é traduzido pela tabela NomeAcorde.
"""
import json
from pathlib import Path

from .cifra import ACORDE_RE, INDICE_NOTA, SUFIXO_VALIDO_RE

ARQUIVO_BASE = Path(__file__).resolve().parent / 'dados' / 'violao_chords_db.json'

# Afinação padrão (MIDI), da 6ª corda (Mi grave) para a 1ª (Mi agudo)
AFINACAO_VIOLAO = [40, 45, 50, 55, 59, 64]
ABERTURA_MAXIMA = 3  # distância máxima entre a casa mais baixa e a mais alta apertadas (acorde gerado)

# Escrita da equipe (o que vem depois da nota) -> tipo na tabela de desenhos
NOMES_PADRAO = {
    '': 'major', 'M': 'major', 'maj': 'major',
    'm': 'minor', 'min': 'minor', '-': 'minor',
    '4': 'sus4', 'sus4': 'sus4', 'sus': 'sus4', '(4)': 'sus4',
    '2': 'sus2', 'sus2': 'sus2',
    '9': 'add9', 'add9': 'add9', '(9)': 'add9', 'add2': 'add9', '(add9)': 'add9',
    'm9': 'madd9', 'm(9)': 'madd9', 'madd9': 'madd9', 'm(add9)': 'madd9', 'm2': 'madd9',
    '7': '7', 'm7': 'm7',
    '7M': 'maj7', 'maj7': 'maj7', 'M7': 'maj7', '(7M)': 'maj7',
    '6': '6', 'm6': 'm6', '6(9)': '69', '69': '69', '6/9': '69', 'm6(9)': 'm69', 'm69': 'm69', 'm6/9': 'm69',
    '7(9)': '9', '7/9': '9', '79': '9', '7(add9)': '9',
    '7(4)': '7sus4', '7sus4': '7sus4', '4/7': '7sus4', '7/4': '7sus4', '74': '7sus4', '47': '7sus4',
    '4(7)': '7sus4', '7(sus4)': '7sus4',
    'm7(9)': 'm9', 'm7/9': 'm9', 'm79': 'm9', 'm7(11)': 'm11', 'm7/11': 'm11', 'm11': 'm11',
    '7M(9)': 'maj9', '7M/9': 'maj9', 'maj9': 'maj9', '7M(13)': 'maj13', 'maj13': 'maj13',
    'm7(b5)': 'm7b5', 'm7b5': 'm7b5', 'm7(5-)': 'm7b5', 'm7/5-': 'm7b5', 'm7-5': 'm7b5', 'ø': 'm7b5',
    '°': 'dim', 'º': 'dim', 'dim': 'dim', 'o': 'dim',
    '°7': 'dim7', 'º7': 'dim7', 'dim7': 'dim7', 'o7': 'dim7',
    '+': 'aug', 'aug': 'aug', '5+': 'aug', '5#': 'aug', '(#5)': 'aug', '#5': 'aug',
    '7(b9)': '7b9', '7b9': '7b9', '7(9-)': '7b9', '7(#9)': '7#9', '7#9': '7#9', '7(9+)': '7#9',
    '7(13)': '13', '13': '13', '7(11)': '11', '11': '11', '9(#11)': '9#11', '7(#11)': '9#11',
    '7(b5)': '7b5', '7b5': '7b5', '7(5-)': '7b5', '7/5-': '7b5',
    '7(#5)': 'aug7', '7#5': 'aug7', '7(5+)': 'aug7', '7+5': 'aug7', '7+': 'aug7',
    'm7M': 'mmaj7', 'm(7M)': 'mmaj7', 'mmaj7': 'mmaj7', 'm7M(9)': 'mmaj9', 'mmaj9': 'mmaj9',
    '7M(#5)': 'maj7#5', '7M(5+)': 'maj7#5', '7M(b5)': 'maj7b5', '7M(5-)': 'maj7b5',
}


# ---------------------------------------------------------------- importação (usada pela migração)

def importar_base(DesenhoAcorde, NomeAcorde=None, arquivo=ARQUIVO_BASE):
    """Recarrega os desenhos da base pública (mantém os da equipe) e cria os nomes padrão que faltarem."""
    dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    DesenhoAcorde.objects.filter(origem='base').delete()
    DesenhoAcorde.objects.bulk_create([
        DesenhoAcorde(instrumento='violao', origem='base', ativo=True, raiz=d['raiz'], tipo=d['tipo'],
                      baixo=d['baixo'], casas=d['casas'], dedos=d['dedos'], pestanas=d['pestanas'],
                      ordem=d['ordem'])
        for d in dados['desenhos']
    ], batch_size=500)
    if NomeAcorde is not None:
        existentes = set(NomeAcorde.objects.values_list('escrita', flat=True))
        NomeAcorde.objects.bulk_create([
            NomeAcorde(escrita=escrita, tipo=tipo, origem='padrao')
            for escrita, tipo in NOMES_PADRAO.items() if escrita not in existentes
        ])
    return len(dados['desenhos'])


# ---------------------------------------------------------------- nome do acorde -> (raiz, tipo, baixo)

def mapa_de_nomes():
    from .models import NomeAcorde
    return dict(NomeAcorde.objects.values_list('escrita', 'tipo'))


def analisar(acorde, nomes):
    """'Bm7/A' -> (11, 'm7', 9).  Tipo desconhecido -> (raiz, None, baixo).  Não é acorde -> None."""
    m = ACORDE_RE.match(acorde or '')
    if not m or not SUFIXO_VALIDO_RE.match(m.group('sufixo')) or m.group('raiz') not in INDICE_NOTA:
        return None
    raiz = INDICE_NOTA[m.group('raiz')]
    baixo = INDICE_NOTA.get(m.group('baixo')) if m.group('baixo') else None
    if baixo == raiz:
        baixo = None  # "A/A" é só A
    return raiz, nomes.get(m.group('sufixo')), baixo


# ---------------------------------------------------------------- acorde com baixo gerado

def _nota_da_corda(corda, casa):
    return AFINACAO_VIOLAO[corda] + casa


def gerar_com_baixo(casas, baixo, raiz=None):
    """Coloca a nota `baixo` na corda mais grave de um desenho. Devolve as novas casas ou None.

    Tenta a 6ª, a 5ª e a 4ª corda; cordas mais graves que a do baixo ficam sem tocar. Se a mão
    precisar abrir demais, as cordas agudas que atrapalham deixam de ser tocadas (ex.: B/D# = x 6 4 4 4 x).
    """
    apertadas = [c for c in casas if c > 0]
    centro = (min(apertadas) + max(apertadas)) / 2 if apertadas else 2
    opcoes = []
    for corda in (0, 1, 2):
        # casas possíveis para a nota do baixo nessa corda, perto de onde a mão já está
        for casa in range(0, 13):
            if (AFINACAO_VIOLAO[corda] + casa) % 12 != baixo:
                continue
            novo = [-1] * corda + [casa] + list(casas[corda + 1:])
            nota_baixo = _nota_da_corda(corda, casa)
            # nenhuma corda mais aguda pode soar mais grave que o baixo
            for i in range(corda + 1, 6):
                if novo[i] >= 0 and _nota_da_corda(i, novo[i]) <= nota_baixo:
                    novo[i] = -1
            # mão aberta demais: tira as cordas agudas (de cima para baixo) que estão longe
            def abertura(c):
                usadas = [x for x in c if x > 0]
                return (max(usadas) - min(usadas)) if usadas else 0
            i = 5
            while abertura(novo) > ABERTURA_MAXIMA and i > corda:
                if novo[i] > 0 and abs(novo[i] - casa) > ABERTURA_MAXIMA - 1 and casa > 0:
                    novo[i] = -1
                i -= 1
            soando = [x for x in novo if x >= 0]
            # cordas mudas no meio do acorde são difíceis de abafar: no máximo uma
            primeira = next(i for i, x in enumerate(novo) if x >= 0)
            ultima = max(i for i, x in enumerate(novo) if x >= 0)
            mudas_no_meio = sum(1 for x in novo[primeira:ultima + 1] if x < 0)
            notas = {_nota_da_corda(i, x) % 12 for i, x in enumerate(novo) if x >= 0}
            tem_raiz = raiz is None or raiz in notas
            if len(soando) >= 3 and tem_raiz and abertura(novo) <= ABERTURA_MAXIMA and mudas_no_meio <= 1:
                distancia = abs(casa - centro) if casa else 0
                # preferência: sem cordas mudas no meio, pelo menos 4 cordas, baixo em corda solta,
                # baixo na corda mais grave, perto de onde a mão já está
                opcoes.append((mudas_no_meio, len(soando) < 4, casa != 0, corda, distancia, -len(soando), novo))
    if not opcoes:
        return None
    return min(opcoes)[-1]


def dedos_simples(casas):
    """Dedos para um desenho gerado. Três ou mais cordas na casa mais baixa viram pestana (dedo 1);
    as outras recebem um dedo cada, da casa mais baixa para a mais alta. Devolve (dedos, pestanas)."""
    apertadas = sorted({c for c in casas if c > 0})
    if not apertadas:
        return [0] * 6, []
    dedos, pestanas, proximo = [0] * 6, [], 1
    menor = apertadas[0]
    if sum(1 for c in casas if c == menor) >= 3:
        for i, c in enumerate(casas):
            if c == menor:
                dedos[i] = 1
        pestanas, proximo = [menor], 2
        apertadas = apertadas[1:]
    for casa in apertadas:
        for i, c in enumerate(casas):
            if c == casa:
                if proximo > 4:
                    return [0] * 6, []  # não dá para indicar os dedos: mostra só as bolinhas
                dedos[i] = proximo
                proximo += 1
    return dedos, pestanas


# ---------------------------------------------------------------- busca dos desenhos

def _como_dict(desenho, gerado=False):
    return {'casas': desenho['casas'], 'dedos': desenho['dedos'], 'pestanas': desenho['pestanas'],
            'gerado': gerado}


def desenhos_violao(nomes_acordes, nomes=None):
    """{nome do acorde: {"desenhos": [...], "aviso": texto ou ""}} para os acordes pedidos.

    Acordes sem desenho possível vêm com a lista vazia (a tela mostra só o nome).
    """
    from .models import DesenhoAcorde

    nomes = mapa_de_nomes() if nomes is None else nomes
    analisados = {nome: analisar(nome, nomes) for nome in nomes_acordes}
    pares = {(a[0], a[1]) for a in analisados.values() if a and a[1]}
    linhas = {}
    if pares:
        consulta = DesenhoAcorde.objects.filter(instrumento='violao', ativo=True,
                                                raiz__in={r for r, _ in pares}, tipo__in={t for _, t in pares})
        # equipe antes da base; depois pela ordem
        for d in sorted(consulta.values('raiz', 'tipo', 'baixo', 'casas', 'dedos', 'pestanas', 'ordem', 'origem'),
                        key=lambda d: (d['origem'] != 'equipe', d['ordem'])):
            linhas.setdefault((d['raiz'], d['tipo'], d['baixo']), []).append(d)

    resultado = {}
    for nome, analise in analisados.items():
        if not analise or not analise[1]:
            resultado[nome] = {'desenhos': [], 'aviso': 'Sem desenho para este acorde'}
            continue
        raiz, tipo, baixo = analise
        exatos = linhas.get((raiz, tipo, baixo), [])
        desenhos = [_como_dict(d) for d in exatos]
        aviso = ''
        if baixo is not None and not desenhos:
            for d in linhas.get((raiz, tipo, None), []):
                casas = gerar_com_baixo(d['casas'], baixo, raiz)
                if casas and all(casas != x['casas'] for x in desenhos):
                    dedos, pestanas = dedos_simples(casas)
                    desenhos.append({'casas': casas, 'dedos': dedos, 'pestanas': pestanas, 'gerado': True})
            if not desenhos:
                # não deu para montar com o baixo: mostra o acorde sem ele e avisa
                from .models import NOMES_NOTAS
                desenhos = [_como_dict(d) for d in linhas.get((raiz, tipo, None), [])]
                if desenhos:
                    aviso = f'Baixo em {NOMES_NOTAS[baixo]}'
        if not desenhos:
            aviso = aviso or 'Sem desenho para este acorde'
        resultado[nome] = {'desenhos': desenhos, 'aviso': aviso}
    return resultado


def diagramas_da_musica(cifra, tom_original='', tom_destino='', nomes=None):
    """Lista [{nome, desenhos, aviso}] com os acordes da música no tom de destino, na ordem em que aparecem."""
    from .cifra import acordes_usados

    acordes = acordes_usados(cifra, tom_original, tom_destino)
    desenhos = desenhos_violao(acordes, nomes)
    return [{'nome': nome, **desenhos[nome]} for nome in acordes]
