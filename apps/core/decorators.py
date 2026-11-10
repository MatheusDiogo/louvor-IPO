from functools import wraps

from django.core.exceptions import PermissionDenied


def requer_lider(view_func):
    """Bloqueia o acesso de quem não é líder."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_lider:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
