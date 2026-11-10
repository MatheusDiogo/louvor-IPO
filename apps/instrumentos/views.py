from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from .models import Instrumento


@login_required
@requer_lider
def instrumentos_view(request):
    instrumentos = Instrumento.objects.all().order_by("nome")
    return render(request, "instrumentos.html", {"instrumentos": instrumentos})


@login_required
@requer_lider
def salvar_instrumento(request):
    if request.method == "POST":
        id = request.POST.get("id")
        nome = request.POST.get("nome", "").strip()

        if nome:
            if id:
                instrumento = get_object_or_404(Instrumento, id=id)
                instrumento.nome = nome
                instrumento.save()
            else:
                Instrumento.objects.create(nome=nome)

    return redirect("instrumentos")


@login_required
@requer_lider
@require_POST
def excluir_instrumento(request, id):
    instrumento = get_object_or_404(Instrumento, id=id)
    instrumento.delete()
    return redirect("instrumentos")
