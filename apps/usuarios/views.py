from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.instrumentos.models import Instrumento

Usuario = get_user_model()


@login_required
@requer_lider
def integrantes_view(request):
    integrantes = Usuario.objects.all().order_by('first_name').prefetch_related('instrumentos')
    instrumentos = Instrumento.objects.all().order_by('nome')  # Para preencher o modal

    return render(request, 'integrantes.html', {
        'integrantes': integrantes,
        'instrumentos': instrumentos
    })


@login_required
@requer_lider
def salvar_integrante(request):
    if request.method != "POST":
        return redirect('integrantes')

    id_usuario = request.POST.get('id')
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    instrumentos_ids = request.POST.getlist('instrumentos')
    is_lider = request.POST.get('is_lider') == 'on'

    duplicado = Usuario.objects.filter(email__iexact=email)
    if id_usuario:
        duplicado = duplicado.exclude(id=id_usuario)
    if duplicado.exists():
        messages.error(request, f'Já existe um integrante com o e-mail {email}.')
        return redirect('integrantes')

    if id_usuario:
        usuario = get_object_or_404(Usuario, id=id_usuario)
        # Mantém o username em sincronia quando ele era o próprio e-mail
        if usuario.username.lower() == (usuario.email or '').lower():
            usuario.username = email
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email
        # Um líder não pode remover a própria liderança (perderia o acesso)
        if usuario != request.user:
            usuario.is_lider = is_lider
        usuario.save()
        messages.success(request, f'{usuario.get_full_name()} atualizado(a).')
    else:
        # Para novos usuários, o username é o e-mail
        usuario = Usuario.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password='louvoripo',
            is_lider=is_lider,
        )
        messages.success(request, f'{usuario.get_full_name()} cadastrado(a). Senha inicial: louvoripo')

    usuario.instrumentos.set(instrumentos_ids)  # Atualiza o ManyToMany
    return redirect('integrantes')


@login_required
@requer_lider
@require_POST
def excluir_integrante(request, id):
    integrante = get_object_or_404(Usuario, id=id)
    if integrante == request.user:
        messages.error(request, 'Você não pode excluir a sua própria conta.')
    else:
        integrante.delete()
        messages.success(request, 'Integrante excluído.')
    return redirect('integrantes')
