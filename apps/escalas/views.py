from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Escala, EscalaMusica
from apps.musicas.models import Musica, Tom
from datetime import datetime
from django.core.exceptions import PermissionDenied

def requer_lider(view_func):
    """Decorator que bloqueia acesso se não for líder."""
    def wrapper(request, *args, **kwargs):
        if not request.user.perfil.is_lider:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def escala_list(request):
    """Lista apenas escalas futuras (data >= hoje)."""
    hoje = timezone.localdate()
    escalas = Escala.objects.filter(data__gte=hoje).order_by('data')
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
            messages.error(request, 'A data da escala deve ser hoje ou uma data futura.')
            return redirect('escala_list')

        if Escala.objects.filter(data=data_obj).exists():
            messages.error(request, f'Já existe uma escala para {data_obj.strftime("%d/%m/%Y")}.')
            return redirect('escala_list')

        escala = Escala.objects.create(data=data_obj, observacao=observacao)
        messages.success(request, f'Escala de {escala.data.strftime("%d/%m/%Y")} criada com sucesso!')
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
            messages.error(request, 'A data da escala deve ser hoje ou uma data futura.')
            return redirect('escala_list')

        # Verifica duplicata de data (ignorando a própria escala)
        if Escala.objects.filter(data=nova_data).exclude(pk=pk).exists():
            messages.error(request, f'Já existe uma escala para {data_obj.strftime("%d/%m/%Y")}.')
            return redirect('escala_list')

        escala.data = data_obj
        escala.observacao = observacao
        escala.save()
        messages.success(request, 'Escala atualizada com sucesso!')
        return redirect('escala_list')

    return redirect('escala_list')


@login_required
@requer_lider
def escala_excluir(request, pk):
    """Exclui uma escala."""
    escala = get_object_or_404(Escala, pk=pk)
    escala.delete()
    messages.success(request, 'Escala excluída com sucesso!')
    return redirect('escala_list')


@login_required
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

    itens = escala.itens.select_related('musica', 'tom').order_by('id')

    return render(request, 'escalas/escala_detalhe.html', {
        'escala': escala,
        'itens': itens,
        'musicas_disponiveis': musicas_disponiveis,
    })


@login_required
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
    return render(request, 'escalas/escala_visualizar.html', {
        'escala': escala,
        'itens': itens,
    })


# API para buscar tons de uma música via AJAX
from django.http import JsonResponse

@login_required
def api_tons_musica(request, musica_id):
    """Retorna os tons disponíveis para uma música em JSON."""
    tons = Tom.objects.filter(musica_id=musica_id).values('id', 'tom')
    return JsonResponse({'tons': list(tons)})