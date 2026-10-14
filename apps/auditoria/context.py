"""Contexto de la petición en curso, para que la auditoría sepa quién hizo el cambio.

Los servicios no reciben la petición HTTP: leen de este contexto, que el middleware
rellena al inicio de cada petición y limpia al terminar. También se puede fijar a mano
desde un comando de gestión o desde una prueba con :func:`usar_usuario`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextoPeticion:
    """Datos de la petición que acompañan a cada registro de auditoría."""

    usuario: Any = None
    usuario_texto: str = ""
    ip: str | None = None
    user_agent: str = ""


_local = threading.local()
_VACIO = ContextoPeticion()


def contexto_actual() -> ContextoPeticion:
    """Devuelve el contexto de la petición en curso (o uno vacío)."""
    return getattr(_local, "contexto", _VACIO)


def establecer_contexto(
    *,
    usuario: Any = None,
    ip: str | None = None,
    user_agent: str = "",
) -> ContextoPeticion:
    """Fija el contexto de la petición actual."""
    texto = ""
    if usuario is not None and getattr(usuario, "is_authenticated", False):
        texto = getattr(usuario, "username", "") or ""
    contexto = ContextoPeticion(
        usuario=usuario if texto else None,
        usuario_texto=texto,
        ip=ip,
        user_agent=user_agent[:250],
    )
    _local.contexto = contexto
    return contexto


def limpiar_contexto() -> None:
    """Borra el contexto al terminar la petición."""
    _local.contexto = _VACIO


@contextmanager
def usar_usuario(usuario: Any) -> Iterator[ContextoPeticion]:
    """Fija un usuario para el bloque de código y restaura el contexto anterior.

    Se usa en comandos de gestión y en pruebas:

    >>> with usar_usuario(admin):  # doctest: +SKIP
    ...     crear_usuario(...)
    """
    anterior = contexto_actual()
    try:
        yield establecer_contexto(usuario=usuario)
    finally:
        _local.contexto = anterior
