from django.urls import path
from .views import ajuda, login_view, home, logout_view
from apps.usuarios.views import cadastro_view

urlpatterns = [
    path("", login_view, name="login"),
    path("home/", home, name="home"),
    path("logout/", logout_view, name="logout"),
    path("cadastro/", cadastro_view, name="cadastro"),
    path("ajuda/", ajuda, name="ajuda"),
]