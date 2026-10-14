"""Middleware que fija el contexto de auditoría en cada petición."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .context import establecer_contexto, limpiar_contexto


class ContextoAuditoriaMiddleware:
    """Deja disponible el usuario, la IP y el navegador para la bitácora.

    Debe colocarse después de ``AuthenticationMiddleware``, porque necesita
    ``request.user``.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = reenviada.split(",")[0].strip() if reenviada else request.META.get("REMOTE_ADDR")
        establecer_contexto(
            usuario=getattr(request, "user", None),
            ip=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        try:
            respuesta = self.get_response(request)
        finally:
            limpiar_contexto()
        return respuesta
