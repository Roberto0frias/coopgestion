"""Validadores compartidos, incluida la cédula dominicana.

.. warning::
   El algoritmo del dígito verificador de la cédula debe validarse con cédulas reales de
   la cooperativa antes de exigirlo en producción (punto abierto P-18). Por eso la
   validación estricta se ofrece como función aparte y no se aplica de forma obligatoria
   en todos los modelos.
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.core.exceptions import ValidationError

PATRON_CEDULA = re.compile(r"^\d{3}-?\d{7}-?\d$")
PATRON_RNC = re.compile(r"^\d{9}$|^\d{3}-?\d{7}-?\d$")


def limpiar_cedula(valor: str) -> str:
    """Quita guiones y espacios de una cédula."""
    return re.sub(r"[\s-]", "", valor or "")


def digito_verificador_cedula(primeros_diez: str) -> int:
    """Calcula el dígito verificador de los primeros 10 dígitos de una cédula dominicana.

    Se multiplica cada dígito por los pesos 1 y 2 alternados; si el producto es mayor o
    igual a 10 se le restan 9 (equivalente a sumar sus cifras). El dígito verificador es
    el complemento a 10 del total, módulo 10.
    """
    if not re.fullmatch(r"\d{10}", primeros_diez):
        raise ValueError("Se esperaban 10 dígitos.")
    pesos = (1, 2, 1, 2, 1, 2, 1, 2, 1, 2)
    total = 0
    for digito, peso in zip(primeros_diez, pesos, strict=True):
        producto = int(digito) * peso
        if producto >= 10:
            producto -= 9
        total += producto
    return (10 - (total % 10)) % 10


def validar_cedula(valor: str) -> str:
    """Valida el formato y el dígito verificador de una cédula dominicana.

    Args:
        valor: Cédula con o sin guiones.

    Returns:
        La cédula normalizada a 11 dígitos.

    Raises:
        django.core.exceptions.ValidationError: si el formato o el dígito no son válidos.
    """
    limpia = limpiar_cedula(valor)
    if not re.fullmatch(r"\d{11}", limpia):
        raise ValidationError("La cédula debe tener 11 dígitos (formato 000-0000000-0).")
    if digito_verificador_cedula(limpia[:10]) != int(limpia[10]):
        raise ValidationError("El dígito verificador de la cédula no es correcto.")
    return limpia


def validar_monto_positivo(valor: Decimal | str) -> Decimal:
    """Convierte a ``Decimal`` y exige que sea mayor que cero.

    Raises:
        ValidationError: si el valor no es un monto válido o no es positivo.
    """
    try:
        monto = Decimal(str(valor))
    except Exception as exc:
        raise ValidationError("El monto no es un número válido.") from exc
    if monto <= Decimal("0"):
        raise ValidationError("El monto debe ser mayor que cero.")
    return monto


def validar_monto_no_negativo(valor: Decimal | str) -> Decimal:
    """Convierte a ``Decimal`` y exige que no sea negativo."""
    try:
        monto = Decimal(str(valor))
    except Exception as exc:
        raise ValidationError("El monto no es un número válido.") from exc
    if monto < Decimal("0"):
        raise ValidationError("El monto no puede ser negativo.")
    return monto
