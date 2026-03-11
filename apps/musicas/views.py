from django.shortcuts import render, redirect, get_object_or_404
from .models import Musica, Tom


def musicas_view(request):

    musicas = Musica.objects.all().order_by("nome")

    return render(
        request,
        "musicas.html",
        {"musicas": musicas}
    )

def salvar_musica(request):
    if request.method == "POST":
        id_musica = request.POST.get('id')
        nome = request.POST.get('nome')
        youtube = request.POST.get('link_youtube')

        if id_musica: # Se tiver ID, estamos editando
            musica = Musica.objects.get(id=id_musica)
            musica.nome = nome
            musica.link_youtube = youtube
            musica.save()
        else: # Se não tiver ID, é uma nova música
            Musica.objects.create(nome=nome, link_youtube=youtube)
            
        return redirect('musicas')
    
def excluir_musica(request, id):
    musica = Musica.objects.get(id=id)
    musica.delete()
    return redirect('musicas')

# Página de detalhes
def detalhes_musica(request, musica_id):
    musica = get_object_or_404(Musica, id=musica_id)
    return render(request, 'detalhes_musica.html', {'musica': musica})

# Salvar o Tom
def salvar_tom(request):
    if request.method == "POST":
        musica_id = request.POST.get('musica_id')
        tom_valor = request.POST.get('tom')
        musica = get_object_or_404(Musica, id=musica_id)

        pdf_file = request.FILES.get('pdf')

        if pdf_file:
            Tom.objects.create(
                musica=musica,
                tom=tom_valor,
                pdf=pdf_file
            )

        return redirect(f'/musicas/{musica_id}/')
    
def excluir_tom(request, id):
    tom = get_object_or_404(Tom, id=id)

    musica_id = tom.musica.id # Guarda o ID para o redirect
    
    tom.delete()
    
    return redirect('detalhes_musica', musica_id=musica_id)