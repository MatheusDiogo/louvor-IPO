from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, get_user_model, login, logout
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

        # Senha correta, mas cadastro ainda não aprovado por um líder
        pendente = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
        if pendente and pendente.check_password(password):
            erro = "Seu cadastro ainda aguarda aprovação de um líder."
        else:
            erro = "E-mail ou senha incorretos"

    return render(request, "login.html", {"erro": erro, "email": email, "next": proximo})


@login_required
def home(request):
    from django.utils import timezone
    from apps.escalas.models import EscalaIntegrante

    hoje = timezone.localdate()

    # Próximo culto em que o usuário está escalado
    proximas = list(
        EscalaIntegrante.objects
        .filter(usuario=request.user, escala__data__gte=hoje)
        .select_related('escala', 'instrumento')
        .order_by('escala__data', 'instrumento__ordem')
    )
    proximo_culto = None
    if proximas:
        escala = proximas[0].escala
        proximo_culto = {
            'escala': escala,
            'funcoes': [ei.instrumento.nome for ei in proximas if ei.escala_id == escala.id],
            'ministra': escala.ministrante_id == request.user.id,
        }
    pendentes = 0
    if request.user.is_lider:
        pendentes = get_user_model().objects.filter(is_active=False).count()

    return render(request, "home.html", {
        "proximo_culto": proximo_culto,
        "hoje": hoje,
        "pendentes": pendentes,
    })


def logout_view(request):
    # Só desloga via POST (evita logout forçado por links/imagens externas)
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return redirect("home")
