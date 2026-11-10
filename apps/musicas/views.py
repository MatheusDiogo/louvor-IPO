from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica

from .models import Musica, Tom


@login_required
def musicas_view(request):
    musicas = sorted(Musica.objects.prefetch_related("tons"), key=lambda m: chave_alfabetica(m.nome))
    return render(request, "musicas.html", {"musicas": musicas})


@login_required
@requer_lider
def salvar_musica(request):
    if request.method == "POST":
        id_musica = request.POST.get('id')
        nome = request.POST.get('nome', '').strip()
        youtube = request.POST.get('link_youtube') or None

        if nome:
            if id_musica:  # Se tiver ID, estamos editando
                musica = get_object_or_404(Musica, id=id_musica)
                musica.nome = nome
                musica.link_youtube = youtube
                musica.save()
            else:  # Se não tiver ID, é uma nova música
                Musica.objects.create(nome=nome, link_youtube=youtube)

    return redirect('musicas')


@login_required
@requer_lider
@require_POST
def excluir_musica(request, id):
    musica = get_object_or_404(Musica, id=id)
    musica.delete()
    return redirect('musicas')


# Página de detalhes
@login_required
def detalhes_musica(request, musica_id):
    musica = get_object_or_404(Musica, id=musica_id)
    return render(request, 'detalhes_musica.html', {'musica': musica})


# Salvar o Tom
@login_required
@requer_lider
def salvar_tom(request):
    if request.method != "POST":
        return redirect('musicas')

    musica_id = request.POST.get('musica_id')
    tom_valor = request.POST.get('tom', '').strip()
    musica = get_object_or_404(Musica, id=musica_id)

    pdf_file = request.FILES.get('pdf')

    if pdf_file and tom_valor:
        Tom.objects.create(musica=musica, tom=tom_valor, pdf=pdf_file)

    return redirect('detalhes_musica', musica_id=musica.id)


@login_required
@requer_lider
@require_POST
def excluir_tom(request, id):
    tom = get_object_or_404(Tom, id=id)
    musica_id = tom.musica.id  # Guarda o ID para o redirect
    tom.delete()
    return redirect('detalhes_musica', musica_id=musica_id)
