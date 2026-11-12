from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from collections import defaultdict

from django.db.models import Count, Max
from .models import Escala, EscalaMusica, EscalaIntegrante
from apps.musicas.cifra import (
    TONS_MAIORES, TONS_MENORES, letra_para_busca, normalizar_tom, opcoes_de_tom, renderizar_html, tom_base,
)
from apps.musicas.cifra_pdf import gerar_pdf
from apps.musicas.models import Musica
from apps.core.decorators import requer_lider
from apps.notificacoes import avisos
from apps.core.utils import chave_alfabetica, subtrair_meses

def urls_proximos_cultos(quantidade=4):
    """Páginas dos próximos cultos para o celular guardar e abrir mesmo sem internet."""
    urls = []
    for escala in Escala.objects.filter(data__gte=timezone.localdate()).order_by('data')[:quantidade]:
        urls += [f'/escalas/{escala.pk}/cifras/', f'/escalas/{escala.pk}/visualizar/']
    return urls


@login_required
def escala_list(request):
    """Lista apenas escalas futuras (data >= hoje)."""
    hoje = timezone.localdate()
    escalas = list(Escala.objects.filter(data__gte=hoje).order_by('data').annotate(total_musicas=Count('itens')))

    # Funções do usuário logado em cada culto (para o aviso "Você está escalado")
    minhas = defaultdict(list)
    for ei in EscalaIntegrante.objects.filter(usuario=request.user, escala__in=escalas).select_related('instrumento'):
        minhas[ei.escala_id].append(ei.instrumento.nome)
    for escala in escalas:
        escala.minhas_funcoes = minhas.get(escala.id, [])
        escala.eu_ministro = escala.ministrante_id == request.user.id

    return render(request, 'escalas/escala_list.html', {
        'escalas': escalas, 'hoje': hoje, 'urls_offline': ['/escalas/', '/musicas/'] + urls_proximos_cultos(),
    })


@login_required
@requer_lider
def escala_criar(request):
    if request.method == 'POST':
        data_str = request.POST.get('data')
        observacao = request.POST.get('observacao', '')

        hoje = timezone.localdate()
        from datetime import date
        data_obj = date.fromisoformat(data_str)

        if data_obj < hoje:
            messages.error(request, 'A data do culto deve ser hoje ou uma data futura.')
            return redirect('escala_list')

        if Escala.objects.filter(data=data_obj).exists():
            messages.error(request, f'Já existe um culto em {data_obj.strftime("%d/%m/%Y")}.')
            return redirect('escala_list')

        escala = Escala.objects.create(data=data_obj, observacao=observacao)
        messages.success(request, f'Culto de {escala.data.strftime("%d/%m/%Y")} criado com sucesso!')
        return redirect('escala_detalhe', pk=escala.pk)

    return redirect('escala_list')


@login_required
@requer_lider
def escala_editar(request, pk):
    """Edita observação e data de uma escala (só permite datas futuras)."""
    escala = get_object_or_404(Escala, pk=pk)

    if request.method == 'POST':
        nova_data = request.POST.get('data')
        observacao = request.POST.get('observacao', '')

        hoje = timezone.localdate()
        from datetime import date
        data_obj = date.fromisoformat(nova_data)

        if data_obj < hoje:
            messages.error(request, 'A data do culto deve ser hoje ou uma data futura.')
            return redirect('escala_list')

        # Verifica duplicata de data (ignorando a própria escala)
        if Escala.objects.filter(data=nova_data).exclude(pk=pk).exists():
            messages.error(request, f'Já existe um culto em {data_obj.strftime("%d/%m/%Y")}.')
            return redirect('escala_list')

        escala.data = data_obj
        escala.observacao = observacao
        escala.save()
        messages.success(request, 'Culto atualizado com sucesso!')
        return redirect('escala_list')

    return redirect('escala_list')


@login_required
@requer_lider
@require_POST
def escala_excluir(request, pk):
    """Exclui uma escala."""
    escala = get_object_or_404(Escala, pk=pk)
    escala.delete()
    messages.success(request, 'Culto excluído com sucesso!')
    proximo = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}):
        return redirect(proximo)
    return redirect('escala_list')


MESES_HISTORICO = 4  # janela usada para "tocada X vezes nos últimos meses"


def _tom_valido(valor, musica):
    """Tom escolhido para o culto; se vazio/inválido, usa o tom original da música."""
    return normalizar_tom(valor) if tom_base(valor) else musica.tom


@login_required
@requer_lider
def escala_detalhe(request, pk):
    """Gerenciar as músicas do culto (e o tom de cada uma)."""
    escala = get_object_or_404(Escala, pk=pk)
    itens = list(escala.itens.select_related('musica').order_by('ordem', 'id'))
    for item in itens:
        opcoes = opcoes_de_tom(item.musica.tom)
        item.opcoes_tom = opcoes if not item.tom or item.tom in opcoes else [item.tom] + opcoes

    na_escala = {item.musica_id for item in itens}
    musicas_disponiveis = sorted(Musica.objects.exclude(id__in=na_escala), key=lambda m: chave_alfabetica(m.nome))

    # Quantas vezes cada música foi tocada nos últimos 4 meses (ajuda a variar o repertório)
    hoje = timezone.localdate()
    recentes = {
        r['musica']: r for r in EscalaMusica.objects
        .filter(escala__data__range=(subtrair_meses(hoje, MESES_HISTORICO), hoje))
        .values('musica').annotate(vezes=Count('id'), ultima=Max('escala__data'))
    }
    for musica in musicas_disponiveis:
        dados = recentes.get(musica.id)
        musica.vezes_recentes = dados['vezes'] if dados else 0
        musica.ultima_vez = dados['ultima'] if dados else None
        musica.letra = letra_para_busca(musica.cifra)  # para buscar também pela letra

    return render(request, 'escalas/escala_detalhe.html', {
        'escala': escala,
        'itens': itens,
        'musicas_disponiveis': musicas_disponiveis,
        'meses_historico': MESES_HISTORICO,
        'tons_maiores': TONS_MAIORES,
        'tons_menores': TONS_MENORES,
    })


@login_required
@requer_lider
@require_POST
def escala_musica_adicionar(request, pk):
    """Adiciona uma música ao culto, no tom escolhido."""
    escala = get_object_or_404(Escala, pk=pk)
    musica = get_object_or_404(Musica, pk=request.POST.get('musica_id') or 0)

    if EscalaMusica.objects.filter(escala=escala, musica=musica).exists():
        messages.error(request, f'"{musica.nome}" já está neste culto.')
    else:
        ultima = escala.itens.aggregate(m=Max('ordem'))['m'] or 0  # nova música entra no fim
        item = EscalaMusica.objects.create(escala=escala, musica=musica, ordem=ultima + 1,
                                           tom=_tom_valido(request.POST.get('tom', ''), musica))
        messages.success(request, f'"{musica.nome}" adicionada!')
        total = escala.itens.count()
        if avisos.repertorio_adicionado(escala, item, total) and total == avisos.MUSICAS_PARA_AVISAR:
            messages.info(request, f'{total} músicas no culto: a equipe escalada foi avisada por notificação.')
    return redirect('escala_detalhe', pk=pk)


@login_required
@requer_lider
@require_POST
def escala_musica_tom(request, item_pk):
    """Troca o tom de uma música no culto."""
    item = get_object_or_404(EscalaMusica.objects.select_related('musica', 'escala'), pk=item_pk)
    tom_antigo = item.tom
    item.tom = _tom_valido(request.POST.get('tom', ''), item.musica)
    item.save(update_fields=['tom'])
    avisos.tom_alterado(item.escala, item, tom_antigo)
    messages.success(request, f'"{item.musica.nome}" agora em {item.tom or "tom original"}.')
    return redirect('escala_detalhe', pk=item.escala_id)


@login_required
@requer_lider
@require_POST
def escala_musica_excluir(request, item_pk):
    """Remove uma música do culto."""
    item = get_object_or_404(EscalaMusica.objects.select_related('musica', 'escala'), pk=item_pk)
    escala_pk = item.escala.pk
    total_antes = item.escala.itens.count()
    nome = item.musica.nome
    item.delete()
    avisos.repertorio_removido(item.escala, nome, total_antes)
    messages.success(request, 'Música removida do culto.')
    return redirect('escala_detalhe', pk=escala_pk)


def pode_ordenar(usuario, escala):
    """Quem ministra o culto e os líderes podem mudar a ordem das músicas."""
    return usuario.is_lider or escala.ministrante_id == usuario.id


@login_required
@require_POST
def escala_musicas_ordem(request, pk):
    """Salva a nova ordem das músicas do culto (lista de ids dos itens, na ordem desejada)."""
    escala = get_object_or_404(Escala, pk=pk)
    if not pode_ordenar(request.user, escala):
        messages.error(request, 'Só quem ministra o culto (ou um líder) pode mudar a ordem das músicas.')
        return redirect('escala_visualizar', pk=pk)

    itens = {item.pk: item for item in escala.itens.all()}
    enviados = [int(i) for i in request.POST.getlist('item') if i.isdigit()]
    # Só aceita se vierem exatamente as músicas do culto (evita perder alguma adicionada nesse meio-tempo)
    if sorted(enviados) != sorted(itens):
        messages.error(request, 'As músicas do culto mudaram enquanto você reordenava. Confira e tente de novo.')
    else:
        for posicao, item_pk in enumerate(enviados, start=1):
            itens[item_pk].ordem = posicao
        EscalaMusica.objects.bulk_update(itens.values(), ['ordem'])
        messages.success(request, 'Ordem das músicas atualizada.')

    proximo = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}):
        return redirect(proximo)
    return redirect('escala_visualizar', pk=pk)


def _equipe(escala):
    """Equipe do culto agrupada por instrumento, na ordem das colunas da escala."""
    equipe = defaultdict(list)
    for ei in escala.integrantes.select_related('instrumento', 'usuario').order_by('instrumento__ordem', 'instrumento__nome', 'pk'):
        equipe[ei.instrumento].append(ei.usuario)
    return equipe


@login_required
def escala_visualizar(request, pk):
    """Visualização do culto (somente leitura): equipe e músicas."""
    escala = get_object_or_404(Escala, pk=pk)
    itens = escala.itens.select_related('musica').order_by('ordem', 'id')
    equipe = _equipe(escala)
    minhas_funcoes = [inst.nome for inst, usuarios in equipe.items() if request.user in usuarios]

    return render(request, 'escalas/escala_visualizar.html', {
        'escala': escala,
        'itens': itens,
        'equipe': list(equipe.items()),
        'minhas_funcoes': minhas_funcoes,
        'pode_ordenar': pode_ordenar(request.user, escala),
    })


@login_required
def escala_cifras(request, pk):
    """Todas as cifras do culto, uma após a outra, já no tom escolhido (para tocar pelo celular)."""
    escala = get_object_or_404(Escala, pk=pk)
    itens = list(escala.itens.select_related('musica').order_by('ordem', 'id'))
    for item in itens:
        item.cifra_html = renderizar_html(item.musica.cifra, item.musica.tom, item.tom)
    return render(request, 'escalas/escala_cifras.html', {'escala': escala, 'itens': itens})


@login_required
def escala_pdf(request, pk):
    """PDF com o repertório do culto (cada música no tom escolhido)."""
    escala = get_object_or_404(Escala, pk=pk)
    itens = escala.itens.select_related('musica').order_by('ordem', 'id')
    titulo = f'Culto {escala.data:%d/%m/%Y}'
    pdf = gerar_pdf([
        {
            'nome': f'{indice}. {item.musica.nome}',
            'cifra': item.musica.cifra,
            'tom_original': item.musica.tom,
            'tom': item.tom,
            'subtitulo': titulo,
        }
        for indice, item in enumerate(itens, start=1)
    ], titulo_documento=titulo)
    resposta = HttpResponse(pdf, content_type='application/pdf')
    resposta['Content-Disposition'] = f'inline; filename="culto-{escala.data:%Y-%m-%d}.pdf"'
    return resposta
