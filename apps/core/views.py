from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme


def _destino_seguro(request, url):
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return url
    return "/home/"


def login_view(request):
    proximo = request.POST.get("next") or request.GET.get("next", "")

    if request.user.is_authenticated:
        return redirect(_destino_seguro(request, proximo))

    erro = None
    email = ""

    if request.method == "POST":
        email = request.POST.get("username", "").strip()
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect(_destino_seguro(request, proximo))
        erro = "E-mail ou senha incorretos"

    return render(request, "login.html", {"erro": erro, "email": email, "next": proximo})


@login_required
def home(request):
    return render(request, "home.html")


def logout_view(request):
    # Só desloga via POST (evita logout forçado por links/imagens externas)
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return redirect("home")
