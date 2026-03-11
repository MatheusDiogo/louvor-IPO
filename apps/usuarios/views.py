from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from apps.instrumentos.models import Instrumento

Usuario = get_user_model()

def integrantes_view(request):
    integrantes = Usuario.objects.all().order_by('first_name')
    instrumentos = Instrumento.objects.all() # Para preencher o select no modal

    return render(request, 'integrantes.html', {
        'integrantes': integrantes,
        'instrumentos': instrumentos
    })

def salvar_integrante(request):
    if request.method == "POST":
        id_usuario = request.POST.get('id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        instrumentos_ids = request.POST.getlist('instrumentos')
        username = request.POST.get('username') or email

        if id_usuario:
            usuario = get_object_or_404(Usuario, id=id_usuario)
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.email = email
            usuario.username = username
        else:
            # Para novos usuários, definimos o username como o email
            usuario = Usuario.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
        
        usuario.save()
        usuario.instrumentos.set(instrumentos_ids) # Atualiza o ManyToMany

        return redirect('integrantes')
    
def excluir_integrante(request, id):
    integrante = get_object_or_404(Usuario, id=id)
    integrante.delete()
    return redirect('integrantes')