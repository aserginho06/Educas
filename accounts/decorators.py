from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Autenticacao obrigatoria.")

            if request.user.role not in roles:
                raise PermissionDenied("Voce nao tem permissao para acessar esta area.")

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
