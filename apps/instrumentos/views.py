from django.shortcuts import render, redirect, get_object_or_404
from .models import Instrumento


def instrumentos_view(request):

    instrumentos = Instrumento.objects.all().order_by("nome")

    return render(
        request,
        "instrumentos.html",
        {"instrumentos": instrumentos}
    )


def salvar_instrumento(request):

    if request.method == "POST":

        id = request.POST.get("id")
        nome = request.POST.get("nome")

        if id:
            instrumento = Instrumento.objects.get(id=id)
            instrumento.nome = nome
            instrumento.save()

        else:
            Instrumento.objects.create(
                nome=nome
            )

    return redirect("instrumentos")


def excluir_instrumento(request, id):

    instrumento = get_object_or_404(Instrumento, id=id)
    instrumento.delete()

    return redirect("instrumentos")