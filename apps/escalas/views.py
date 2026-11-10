from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from collections import defaultdict

from django.db.models import Count
from .models import Escala, EscalaMusica, EscalaIntegrante
from apps.musicas.models import Musica, Tom
from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica

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

    return render(request, 'escalas/escala_list.html', {'escalas': escalas, 'hoje': hoje})


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


@login_required
@requer_lider
def escala_detalhe(request, pk):
    """Detalhe/edição da escala: adicionar músicas com tom."""
    escala = get_object_or_404(Escala, pk=pk)

    # IDs de músicas já adicionadas nessa escala
    musicas_na_escala_ids = escala.itens.values_list('musica_id', flat=True)

    # Músicas disponíveis (com pelo menos 1 tom cadastrado, ainda não na escala)
    musicas_disponiveis = Musica.objects.filter(
        tons__isnull=False
    ).exclude(
        id__in=musicas_na_escala_ids
    ).distinct()
    musicas_disponiveis = sorted(musicas_disponiveis, key=lambda m: chave_alfabetica(m.nome))

    itens = escala.itens.select_related('musica', 'tom').order_by('id')

    return render(request, 'escalas/escala_detalhe.html', {
        'escala': escala,
        'itens': itens,
        'musicas_disponiveis': musicas_disponiveis,
    })


@login_required
@requer_lider
def escala_musica_adicionar(request, pk):
    """Adiciona uma música (com tom) à escala."""
    escala = get_object_or_404(Escala, pk=pk)

    if request.method == 'POST':
        musica_id = request.POST.get('musica_id')
        tom_id = request.POST.get('tom_id')

        if not musica_id or not tom_id:
            messages.error(request, 'Selecione a música e o tom.')
            return redirect('escala_detalhe', pk=pk)

        musica = get_object_or_404(Musica, pk=musica_id)
        tom = get_object_or_404(Tom, pk=tom_id, musica=musica)

        if EscalaMusica.objects.filter(escala=escala, musica=musica).exists():
            messages.error(request, f'"{musica.nome}" já está nessa escala.')
            return redirect('escala_detalhe', pk=pk)

        EscalaMusica.objects.create(escala=escala, musica=musica, tom=tom)
        messages.success(request, f'"{musica.nome}" adicionada com sucesso!')

    return redirect('escala_detalhe', pk=pk)


@login_required
@requer_lider
@require_POST
def escala_musica_excluir(request, item_pk):
    """Remove uma música da escala."""
    item = get_object_or_404(EscalaMusica, pk=item_pk)
    escala_pk = item.escala.pk
    item.delete()
    messages.success(request, 'Música removida da escala.')
    return redirect('escala_detalhe', pk=escala_pk)


@login_required
def escala_visualizar(request, pk):
    """Visualização pública da escala (somente leitura, para ver PDFs)."""
    escala = get_object_or_404(Escala, pk=pk)
    itens = escala.itens.select_related('musica', 'tom').order_by('id')

    # Equipe do culto agrupada por instrumento, na ordem das colunas da escala
    equipe = defaultdict(list)
    for ei in escala.integrantes.select_related('instrumento', 'usuario').order_by('instrumento__ordem', 'instrumento__nome', 'pk'):
        equipe[ei.instrumento].append(ei.usuario)
    minhas_funcoes = [inst.nome for inst, usuarios in equipe.items() if request.user in usuarios]

    return render(request, 'escalas/escala_visualizar.html', {
        'escala': escala,
        'itens': itens,
        'equipe': list(equipe.items()),
        'minhas_funcoes': minhas_funcoes,
    })


# API para buscar tons de uma música via AJAX
from django.http import JsonResponse

@login_required
def api_tons_musica(request, musica_id):
    """Retorna os tons disponíveis para uma música em JSON."""
    tons = Tom.objects.filter(musica_id=musica_id).values('id', 'tom')
    return JsonResponse({'tons': list(tons)})