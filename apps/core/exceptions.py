"""Excepciones de negocio de COOPGESTION.

Las vistas no capturan errores técnicos: los servicios levantan estas excepciones y la
capa de presentación las traduce a mensajes comprensibles para el usuario.
"""

from __future__ import annotations


class ErrorDeNegocio(Exception):
    """Error de una regla de negocio. El mensaje se muestra al usuario."""


class ErrorDeValidacion(ErrorDeNegocio):
    """Los datos recibidos no cumplen una regla de negocio."""


class ErrorDeConcurrencia(ErrorDeNegocio):
    """Otra operación modificó el registro; conviene reintentar."""


class ErrorDeConfiguracion(ErrorDeNegocio):
    """Falta configuración necesaria para operar (parámetro, secuencia, tasa)."""


class ErrorFiscal(ErrorDeNegocio):
    """Se intentó una operación fiscal no habilitada (por ejemplo, emitir NCF)."""
