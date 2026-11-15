"""Tela "Avisos programados": só o administrador (superusuário) cadastra, testa e acompanha os envios."""
import json
from functools import wraps

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import programados
from .models import AvisoProgramado, EnvioAviso

APPS_DO_SITE = ('usuarios', 'instrumentos', 'musicas', 'escalas', 'notificacoes')
PAGINAS = [
    ('/home/', 'Início'),
    ('/escalas/', 'Culto (próximos cultos)'),
    ('/escalas/equipe/', 'Escalas do mês'),
    ('/escalas/disponibilidade/', 'Minha disponibilidade'),
    ('/musicas/', 'Músicas'),
]
VARIAVEIS_FIXAS = [
    ('nome', 'primeiro nome da pessoa'),
    ('nome_completo', 'nome completo'),
    ('hoje', 'data de hoje (dd/mm)'),
    ('proximo_culto', 'data do próximo culto'),
    ('mes_seguinte', 'mês aberto para informar a disponibilidade'),
    ('prazo', 'prazo desse mês (dd/mm)'),
]
# Data de hoje em Recife (o banco trabalha em UTC: depois das 21h de Recife já seria "amanhã")
HOJE_SQL = "(now() AT TIME ZONE 'America/Recife')::date"
# Último domingo do mês atual; o prazo da disponibilidade é a sexta antes dele (domingo - 2)
ULTIMO_DOMINGO_SQL = ("(date_trunc('month', {h}) + interval '1 month - 1 day')::date"
                      " - EXTRACT(DOW FROM date_trunc('month', {h}) + interval '1 month - 1 day')::int").format(h=HOJE_SQL)

EXEMPLOS_SQL = [
    ('Todos os integrantes ativos', 'SELECT id FROM usuarios_usuario WHERE is_active'),
    ('Só os líderes', 'SELECT id FROM usuarios_usuario WHERE is_active AND is_lider'),
    ('Quem toca um instrumento (com a variável {instrumento})',
     "SELECT u.id, i.nome AS instrumento\nFROM usuarios_usuario u\n"
     "JOIN usuarios_usuario_instrumentos ui ON ui.usuario_id = u.id\n"
     "JOIN instrumentos_instrumento i ON i.id = ui.instrumento_id\nWHERE u.is_active AND i.nome = 'Violão'"),
    ('Escalados no próximo culto (com {instrumento} e {data_culto})',
     "SELECT u.id, i.nome AS instrumento, e.data AS data_culto\nFROM escalas_escalaintegrante ei\n"
     "JOIN escalas_escala e ON e.id = ei.escala_id\nJOIN usuarios_usuario u ON u.id = ei.usuario_id\n"
     "JOIN instrumentos_instrumento i ON i.id = ei.instrumento_id\n"
     f"WHERE e.data = (SELECT MIN(data) FROM escalas_escala WHERE data >= {HOJE_SQL})"),
    ('Quem ainda não marcou nenhuma indisponibilidade no próximo mês',
     "SELECT u.id FROM usuarios_usuario u\nWHERE u.is_active AND NOT EXISTS (\n"
     "  SELECT 1 FROM escalas_indisponibilidade d\n  WHERE d.usuario_id = u.id\n"
     f"    AND d.data >= date_trunc('month', {HOJE_SQL}) + interval '1 month'\n"
     f"    AND d.data < date_trunc('month', {HOJE_SQL}) + interval '2 months')"),
    ('Disponibilidade: só na SEGUNDA da semana do prazo (use com o cron 0 9 * * 1)',
     "-- Toda segunda o cron roda, mas só a segunda da semana do prazo devolve alguém\n"
     f"SELECT id FROM usuarios_usuario\nWHERE is_active\n  AND {HOJE_SQL} = {ULTIMO_DOMINGO_SQL} - 6"),
    ('Disponibilidade: só na SEXTA do prazo, último dia (use com o cron 0 9 * * 5)',
     "-- Toda sexta o cron roda, mas só a sexta do prazo devolve alguém\n"
     f"SELECT id FROM usuarios_usuario\nWHERE is_active\n  AND {HOJE_SQL} = {ULTIMO_DOMINGO_SQL} - 2"),
]


def requer_superusuario(view):
    @wraps(view)
    def interna(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise Http404  # para os outros, a tela "não existe"
        return view(request, *args, **kwargs)
    return login_required(interna)


def _tabelas():
    """Tabelas e colunas do site (ajuda para escrever o SELECT)."""
    resultado = []
    for modelo in apps.get_models():
        if modelo._meta.app_label not in APPS_DO_SITE:
            continue
        colunas = [c.column for c in modelo._meta.concrete_fields if c.column != 'password']
        resultado.append({'tabela': modelo._meta.db_table, 'colunas': colunas})
        for m2m in modelo._meta.local_many_to_many:
            tabela = m2m.remote_field.through._meta
            if tabela.auto_created:
                resultado.append({'tabela': tabela.db_table, 'colunas': [c.column for c in tabela.concrete_fields]})
    return sorted(resultado, key=lambda t: t['tabela'])


def _descricao_agenda(aviso):
    return f'cron: {aviso.cron}'


@requer_superusuario
def avisos_lista(request):
    avisos = list(AvisoProgramado.objects.all())
    for aviso in avisos:
        aviso.descricao = _descricao_agenda(aviso)
        proximos = programados.proximos_envios(aviso, 1) if aviso.ativo else []
        aviso.proximo = proximos[0] if proximos else None
        aviso.ultimo = aviso.envios.filter(teste=False).first()
    return render(request, 'notificacoes/avisos_lista.html', {
        'avisos': avisos,
        'historico': EnvioAviso.objects.select_related('aviso')[:30],
        'agora': timezone.localtime(),
    })


def _salvar(request, aviso):
    """Preenche o aviso com o formulário. Devolve a lista de erros (vazia = pode salvar)."""
    p = request.POST
    erros = []
    aviso.nome = p.get('nome', '').strip()[:100]
    aviso.ativo = p.get('ativo') == 'on'
    aviso.cron = ' '.join(p.get('cron', '').split())[:100]
    aviso.titulo = p.get('titulo', '').strip()[:120]
    aviso.mensagem = p.get('mensagem', '').strip()
    aviso.url = p.get('url', '').strip()[:200] or '/home/'
    aviso.consulta = p.get('consulta', '').strip()
    if not aviso.nome:
        erros.append('Dê um nome ao aviso.')
    if not aviso.titulo or not aviso.mensagem:
        erros.append('Preencha o título e a mensagem.')
    if not aviso.url.startswith('/'):
        erros.append('A página deve ser um endereço do site, começando com "/" (ex.: /escalas/).')
    try:
        programados.ler_cron(aviso.cron)
    except programados.ErroCron as erro:
        erros.append(f'Cron: {erro}')
    try:
        programados.destinatarios(aviso.consulta)
    except programados.ErroConsulta as erro:
        erros.append(str(erro))
    return erros


@requer_superusuario
def aviso_editar(request, pk=None):
    aviso = get_object_or_404(AvisoProgramado, pk=pk) if pk else AvisoProgramado(
        consulta=EXEMPLOS_SQL[0][1], cron='0 9 * * 1', url='/home/')
    erros = []
    if request.method == 'POST':
        erros = _salvar(request, aviso)
        if not erros:
            aviso.save()
            messages.success(request, f'Aviso "{aviso.nome}" salvo.')
            return redirect('avisos_lista')
    return render(request, 'notificacoes/aviso_form.html', {
        'aviso': aviso, 'erros': erros, 'paginas': PAGINAS, 'variaveis': VARIAVEIS_FIXAS,
        'exemplos': EXEMPLOS_SQL, 'tabelas': _tabelas(), 'historico': aviso.envios.all()[:15] if aviso.pk else [],
    })


@requer_superusuario
@require_POST
def aviso_excluir(request, pk):
    aviso = get_object_or_404(AvisoProgramado, pk=pk)
    aviso.delete()
    messages.success(request, f'Aviso "{aviso.nome}" excluído.')
    return redirect('avisos_lista')


@requer_superusuario
@require_POST
def aviso_ativo(request, pk):
    aviso = get_object_or_404(AvisoProgramado, pk=pk)
    aviso.ativo = not aviso.ativo
    aviso.save(update_fields=['ativo'])
    messages.success(request, f'Aviso "{aviso.nome}" {"ativado" if aviso.ativo else "pausado"}.')
    return redirect('avisos_lista')


@requer_superusuario
@require_POST
def aviso_enviar_teste(request, pk):
    """Manda o aviso só para quem está testando, com o texto montado (e "[Teste]" no título)."""
    aviso = get_object_or_404(AvisoProgramado, pk=pk)
    envio = programados.enviar(aviso, f'teste-{aviso.pk}-{timezone.now():%Y%m%d%H%M%S%f}', teste_para=request.user)
    if envio.erro:
        messages.error(request, f'Não foi possível enviar o teste: {envio.erro}')
    elif not envio.celulares:
        messages.warning(request, 'Teste montado, mas nenhum celular seu recebeu: ative as notificações neste aparelho (sino no topo).')
    else:
        messages.success(request, 'Teste enviado para os seus celulares.')
    return redirect('aviso_editar', pk=aviso.pk)


@requer_superusuario
@require_POST
def aviso_testar(request):
    """Prévia (sem enviar nada): quem recebe, as variáveis e como fica a mensagem; e os próximos envios."""
    try:
        dados = json.loads(request.body or '{}')
    except ValueError:
        return JsonResponse({'ok': False, 'erro': 'Dados inválidos.'}, status=400)
    resposta = {'ok': True}
    # próximos envios
    try:
        resposta['proximos'] = [f'{m:%d/%m/%Y %H:%M}' for m in programados.proximos_cron(dados.get('cron', ''), None, 5)]
    except programados.ErroCron as erro:
        resposta['erro_cron'] = str(erro)
    # destinatários e prévia
    try:
        pessoas = programados.destinatarios(dados.get('consulta', ''))
    except programados.ErroConsulta as erro:
        resposta['erro_consulta'] = str(erro)
        return JsonResponse(resposta)
    from django.contrib.auth import get_user_model
    usuarios = {u.pk: u for u in get_user_model().objects.filter(pk__in=pessoas)}
    gerais = programados.variaveis_gerais()
    linhas = []
    for uid, extras in list(pessoas.items())[:30]:
        u = usuarios[uid]
        variaveis = {**gerais, **programados.variaveis_da_pessoa(u), **extras}
        linhas.append({'id': uid, 'nome': u.get_full_name() or u.email, 'extras': extras,
                       'titulo': programados.montar(dados.get('titulo', ''), variaveis),
                       'mensagem': programados.montar(dados.get('mensagem', ''), variaveis)})
    resposta.update({
        'total': len(pessoas),
        'extras': sorted({k for v in pessoas.values() for k in v}),
        'linhas': linhas,
    })
    return JsonResponse(resposta)
