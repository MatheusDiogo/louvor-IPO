"""Avisos programados: quando enviar (cron), para quem (SELECT) e o texto.

O serviço cron do Railway roda `python manage.py enviar_avisos` de hora em hora; a cada rodada,
os avisos que estão na hora saem uma vez só (o histórico EnvioAviso guarda a chave do período).
"""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.formats import date_format

from . import servico

# ---------------------------------------------------------------- cron (minuto hora dia mês dia-da-semana)

CAMPOS_CRON = [('minuto', 0, 59), ('hora', 0, 23), ('dia', 1, 31), ('mes', 1, 12), ('semana', 0, 7)]
NOMES_SEMANA = {'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6,
                'dom': 0, 'seg': 1, 'ter': 2, 'qua': 3, 'qui': 4, 'sex': 5, 'sab': 6}


class ErroCron(ValueError):
    pass


def _campo(texto, minimo, maximo, nome):
    valores = set()
    for parte in texto.split(','):
        passo = 1
        if '/' in parte:
            parte, passo_txt = parte.split('/', 1)
            if not passo_txt.isdigit() or int(passo_txt) < 1:
                raise ErroCron(f'Passo inválido em "{nome}".')
            passo = int(passo_txt)
        if parte == '*':
            ini, fim = minimo, maximo
        elif '-' in parte:
            a, b = parte.split('-', 1)
            ini, fim = _numero(a, nome), _numero(b, nome)
        else:
            ini = _numero(parte, nome)
            fim = maximo if passo > 1 else ini
        if not (minimo <= ini <= maximo and minimo <= fim <= maximo and ini <= fim):
            raise ErroCron(f'Valor fora do intervalo em "{nome}" ({minimo} a {maximo}).')
        valores.update(range(ini, fim + 1, passo))
    return valores


def _numero(texto, nome):
    texto = texto.strip().lower()
    if texto in NOMES_SEMANA and nome == 'semana':
        return NOMES_SEMANA[texto]
    if not texto.isdigit():
        raise ErroCron(f'Valor inválido em "{nome}": {texto or "(vazio)"}.')
    return int(texto)


def ler_cron(expressao):
    """'0 9 * * 1' -> dict com os conjuntos de cada campo. Erro de escrita -> ErroCron."""
    partes = (expressao or '').split()
    if len(partes) != 5:
        raise ErroCron('Use 5 campos: minuto hora dia mês dia-da-semana (ex.: 0 9 * * 1).')
    cron = {}
    for texto, (nome, minimo, maximo) in zip(partes, CAMPOS_CRON):
        cron[nome] = _campo(texto.lower(), minimo, maximo, nome)
        cron[nome + '_livre'] = texto == '*'
    if 7 in cron['semana']:
        cron['semana'].add(0)  # 7 também é domingo
    return cron


def _dia_confere(cron, dia):
    semana = (dia.weekday() + 1) % 7  # cron: domingo = 0
    no_dia, na_semana = dia.day in cron['dia'], semana in cron['semana']
    if not cron['dia_livre'] and not cron['semana_livre']:
        return no_dia or na_semana  # regra do cron: com os dois restritos, vale qualquer um
    return no_dia and na_semana


def cron_na_hora(cron, momento):
    """O cron cai em algum minuto desta hora? (o envio acontece no começo da hora)"""
    return (momento.month in cron['mes'] and _dia_confere(cron, momento.date())
            and momento.hour in cron['hora'] and bool(cron['minuto']))


def proximos_cron(expressao, a_partir=None, quantidade=5):
    cron = ler_cron(expressao)
    momento = (a_partir or timezone.localtime()).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    resultado = []
    for _ in range(24 * 400):  # até ~1 ano e 1 mês à frente
        if cron_na_hora(cron, momento):
            resultado.append(momento.replace(minute=min(cron['minuto'])))
            if len(resultado) == quantidade:
                break
        momento += timedelta(hours=1)
    return resultado


# ---------------------------------------------------------------- consulta (somente leitura)

PROIBIDAS = re.compile(
    r'\b(insert|update|delete|merge|upsert|drop|alter|create|truncate|grant|revoke|copy|vacuum|analyze|reindex|'
    r'cluster|call|do|set|reset|lock|comment|refresh|execute|prepare|deallocate|listen|notify|attach|detach|'
    r'pragma|pg_sleep|pg_terminate_backend|pg_cancel_backend|pg_read_file|pg_read_binary_file|pg_ls_dir|'
    r'lo_import|lo_export|dblink)\b', re.IGNORECASE)
LIMITE_LINHAS = 2000


class ErroConsulta(ValueError):
    pass


def _limpar_sql(sql):
    sem_comentarios = re.sub(r'--[^\n]*|/\*.*?\*/', ' ', sql or '', flags=re.DOTALL)
    texto = sem_comentarios.strip().rstrip(';').strip()
    if not texto:
        raise ErroConsulta('Escreva a consulta.')
    if ';' in texto:
        raise ErroConsulta('Use uma única consulta (sem ";" no meio).')
    if not re.match(r'^(select|with)\b', texto, re.IGNORECASE):
        raise ErroConsulta('A consulta precisa começar com SELECT (ou WITH).')
    proibida = PROIBIDAS.search(re.sub(r"'(?:[^']|'')*'", "''", texto))  # ignora o que está entre aspas
    if proibida:
        raise ErroConsulta(f'Comando não permitido na consulta: {proibida.group(1).upper()}.')
    return texto


def executar_consulta(sql):
    """Roda o SELECT numa transação somente leitura. Devolve (colunas, linhas)."""
    texto = _limpar_sql(sql)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute('SET TRANSACTION READ ONLY')
                    cursor.execute("SET LOCAL statement_timeout = '5s'")
                elif connection.vendor == 'sqlite':
                    cursor.execute('PRAGMA query_only = ON')
                try:
                    cursor.execute(texto)
                    colunas = [c[0] for c in cursor.description or []]
                    linhas = cursor.fetchmany(LIMITE_LINHAS)
                finally:
                    if connection.vendor == 'sqlite':
                        cursor.execute('PRAGMA query_only = OFF')
    except ErroConsulta:
        raise
    except Exception as erro:  # erro de SQL: devolve a mensagem do banco
        raise ErroConsulta(f'Erro na consulta: {erro}') from erro
    if not colunas:
        raise ErroConsulta('A consulta não devolveu colunas.')
    return colunas, linhas


def destinatarios(sql):
    """{id do integrante: {coluna: valor}} a partir do SELECT (coluna "id", ou a primeira)."""
    colunas, linhas = executar_consulta(sql)
    nomes = [c.lower() for c in colunas]
    pos_id = nomes.index('id') if 'id' in nomes else 0
    por_pessoa = {}
    for linha in linhas:
        try:
            uid = int(linha[pos_id])
        except (TypeError, ValueError):
            raise ErroConsulta(f'A coluna "{colunas[pos_id]}" precisa ter o id dos integrantes (números).')
        extras = por_pessoa.setdefault(uid, {})
        for i, nome in enumerate(nomes):
            if i == pos_id:
                continue
            valor = _formatar(linha[i])
            # mesma pessoa em várias linhas: junta os valores ("Violão, Voz")
            if nome in extras and valor and valor not in extras[nome].split(', '):
                extras[nome] = f'{extras[nome]}, {valor}'
            elif nome not in extras:
                extras[nome] = valor
    ativos = set(get_user_model().objects.filter(pk__in=por_pessoa, is_active=True).values_list('pk', flat=True))
    return {uid: v for uid, v in por_pessoa.items() if uid in ativos}


def _formatar(valor):
    if valor is None:
        return ''
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y %H:%M') if hasattr(valor, 'hour') else valor.strftime('%d/%m/%Y')
    return str(valor)


# ---------------------------------------------------------------- variáveis e texto

VARIAVEL_RE = re.compile(r'\{(\w+)\}')


def variaveis_gerais(hoje=None):
    from apps.escalas.disponibilidade import prazo_do_mes, proximo_mes_aberto
    from apps.escalas.models import Escala

    hoje = hoje or timezone.localdate()
    mes = proximo_mes_aberto(hoje)
    proximo = Escala.objects.filter(data__gte=hoje).order_by('data').first()
    return {
        'hoje': hoje.strftime('%d/%m'),
        'mes_seguinte': date_format(mes, 'F').lower(),
        'prazo': prazo_do_mes(mes).strftime('%d/%m'),
        'proximo_culto': proximo.data.strftime('%d/%m') if proximo else '',
    }


def variaveis_da_pessoa(usuario):
    return {'nome': usuario.first_name or usuario.get_full_name() or usuario.email,
            'nome_completo': usuario.get_full_name() or usuario.first_name or usuario.email}


def montar(texto, variaveis):
    """Troca {variavel} pelo valor; variável desconhecida fica como está (para aparecer no teste)."""
    return VARIAVEL_RE.sub(lambda m: str(variaveis[m.group(1).lower()]) if m.group(1).lower() in variaveis else m.group(0),
                           texto or '')


def mensagens_do_aviso(aviso, hoje=None):
    """{id: (título, corpo)} para cada destinatário do aviso."""
    gerais = variaveis_gerais(hoje)
    pessoas = destinatarios(aviso.consulta)
    usuarios = {u.pk: u for u in get_user_model().objects.filter(pk__in=pessoas)}
    mensagens = {}
    for uid, extras in pessoas.items():
        variaveis = {**gerais, **variaveis_da_pessoa(usuarios[uid]), **extras}
        mensagens[uid] = (montar(aviso.titulo, variaveis), montar(aviso.mensagem, variaveis))
    return mensagens


# ---------------------------------------------------------------- quando enviar

def chave_do_periodo(aviso, momento):
    """Identifica o "envio" do aviso neste momento (uma vez por hora), ou None se não é hora dele."""
    try:
        cron = ler_cron(aviso.cron)
    except ErroCron:
        return None
    if cron_na_hora(cron, momento):
        return f'aviso-{aviso.pk}-{momento:%Y%m%d%H}'
    return None


def proximos_envios(aviso, quantidade=3):
    try:
        return proximos_cron(aviso.cron, timezone.localtime(), quantidade)
    except ErroCron:
        return []


def enviar(aviso, chave, teste_para=None):
    """Envia o aviso (uma vez por chave) e grava no histórico. teste_para: só para essa pessoa."""
    from .models import EnvioAviso

    try:
        with transaction.atomic():
            envio = EnvioAviso.objects.create(aviso=aviso, chave=chave, teste=bool(teste_para))
    except IntegrityError:
        return None  # já enviado neste período
    try:
        mensagens = mensagens_do_aviso(aviso)
        if teste_para is not None:
            # teste: usa os dados da própria pessoa se ela estiver na consulta; senão, os do primeiro
            escolhida = mensagens.get(teste_para.pk) or next(iter(mensagens.values()), None)
            if escolhida is None:
                gerais = {**variaveis_gerais(), **variaveis_da_pessoa(teste_para)}
                escolhida = (montar(aviso.titulo, gerais), montar(aviso.mensagem, gerais))
            mensagens = {teste_para.pk: (f'[Teste] {escolhida[0]}', escolhida[1])}
        envio.pessoas = len(mensagens)
        envio.celulares = servico.enviar_personalizado(mensagens, url=aviso.url or '/home/',
                                                       tag=f'aviso-{aviso.pk}', em_segundo_plano=False)
    except Exception as erro:
        envio.erro = str(erro)[:2000]
    envio.save(update_fields=['pessoas', 'celulares', 'erro'])
    return envio


def rodar(momento=None):
    """Chamado de hora em hora: envia os avisos ativos que estão na hora. Devolve os envios feitos."""
    from .models import AvisoProgramado

    momento = momento or timezone.localtime()
    feitos = []
    for aviso in AvisoProgramado.objects.filter(ativo=True):
        chave = chave_do_periodo(aviso, momento)
        if chave:
            envio = enviar(aviso, chave)
            if envio:
                feitos.append(envio)
    return feitos
