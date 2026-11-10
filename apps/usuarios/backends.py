from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOuUsernameBackend(ModelBackend):
    """Permite login pelo e-mail (sem diferenciar maiúsculas) ou pelo username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        Usuario = get_user_model()
        identificador = username.strip()
        usuario = (
            Usuario.objects.filter(email__iexact=identificador).first()
            or Usuario.objects.filter(username=identificador).first()
        )
        if usuario is None:
            Usuario().set_password(password)  # tempo constante contra enumeração de usuários
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
