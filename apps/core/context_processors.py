"""Procesadores de contexto: menú de navegación según el rol del usuario.

El menú se construye a partir de permisos, no de listas de roles escritas a mano. Así,
cuando un módulo declare sus permisos en fases posteriores, basta con añadir la entrada
aquí y el rol que los tenga verá la opción automáticamente.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.urls import NoReverseMatch, reverse

# Cada entrada declara el permiso necesario; ``None`` significa visible para cualquiera
# que haya iniciado sesión.
ELEMENTOS_MENU: list[dict[str, Any]] = [
    {"nombre": "Inicio", "url_name": "core:inicio", "permiso": None, "icono": "casa"},
    {
        "nombre": "Usuarios",
        "url_name": "usuarios:lista",
        "permiso": "usuarios.puede_gestionar_usuarios",
        "icono": "personas",
    },
    {
        "nombre": "Roles",
        "url_name": "usuarios:roles",
        "permiso": "usuarios.puede_gestionar_usuarios",
        "icono": "escudo",
    },
    {
        "nombre": "Parámetros",
        "url_name": "core:parametros",
        "permiso": "core.puede_gestionar_parametros",
        "icono": "ajustes",
    },
    {
        "nombre": "Auditoría",
        "url_name": "auditoria:lista",
        "permiso": "auditoria.puede_ver_auditoria",
        "icono": "lista",
    },
]


def navegacion(request) -> dict[str, Any]:
    """Devuelve las entradas de menú que el usuario puede ver y los datos de la cooperativa."""
    usuario = getattr(request, "user", None)
    elementos: list[dict[str, Any]] = []

    for item in ELEMENTOS_MENU:
        permiso = item["permiso"]
        if permiso is not None:
            if usuario is None or not usuario.is_authenticated:
                continue
            if not usuario.has_perm(permiso):
                continue
        try:
            url = reverse(item["url_name"])
        except NoReverseMatch:  # pragma: no cover - protección ante rutas aún no creadas
            continue
        elementos.append({**item, "url": url})

    return {
        "menu_navegacion": elementos,
        "coopgestion": getattr(settings, "COOPGESTION", {}),
    }
