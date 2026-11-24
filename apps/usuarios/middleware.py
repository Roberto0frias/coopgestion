from django.shortcuts import redirect
from django.urls import reverse


class CambioPasswordObligatorioMiddleware:
    """Limita la sesión a actualizar la contraseña marcada como obligatoria."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if (
            usuario.is_authenticated
            and usuario.debe_cambiar_password
            and request.path not in (reverse("password_change"), reverse("logout"))
        ):
            return redirect("password_change")
        return self.get_response(request)
