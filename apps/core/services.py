"""Servicios del núcleo: parámetros, secuencias documentales e idempotencia.

Toda la lógica de negocio vive aquí, nunca en las vistas ni en las plantillas.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from .exceptions import ErrorDeConcurrencia, ErrorDeConfiguracion, ErrorDeValidacion
from .models import OperacionIdempotente, ParametroSistema, SecuenciaDocumental, Sucursal

logger = logging.getLogger(__name__)


def _es_verdadero(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in {"1", "true", "verdadero", "si", "sí", "yes"}


def _a_json(valor: Any) -> str:
    if isinstance(valor, str):
        json.loads(valor)  # valida antes de guardar
        return valor
    return json.dumps(valor, ensure_ascii=False, sort_keys=True)


#: Convierte el valor recibido al texto que se guarda, según el tipo declarado.
#: Se define después de las funciones auxiliares porque las referencia directamente.
_CONVERSIONES: dict[str, Callable[[Any], str]] = {
    ParametroSistema.TipoDato.TEXTO: str,
    ParametroSistema.TipoDato.ENTERO: lambda v: str(int(v)),
    ParametroSistema.TipoDato.DECIMAL: lambda v: str(Decimal(str(v)).quantize(Decimal("0.01"))),
    ParametroSistema.TipoDato.BOOLEANO: lambda v: "true" if _es_verdadero(v) else "false",
    ParametroSistema.TipoDato.JSON: _a_json,
}


# --------------------------------------------------------------------------- #
# Parámetros del sistema
# --------------------------------------------------------------------------- #
def obtener_parametro(clave: str, por_defecto: Any = None) -> Any:
    """Devuelve el valor convertido de un parámetro.

    Args:
        clave: Clave del parámetro (por ejemplo ``UMBRAL_RETIRO_DOBLE_FIRMA``).
        por_defecto: Valor a devolver si el parámetro no existe.

    Returns:
        El valor convertido a su tipo, o ``por_defecto``.
    """
    try:
        parametro = ParametroSistema.objects.get(clave=clave)
    except ParametroSistema.DoesNotExist:
        return por_defecto
    try:
        return parametro.valor_convertido()
    except (ValueError, InvalidOperation, TypeError) as exc:
        logger.warning("Parámetro %s con valor inválido: %r", clave, parametro.valor)
        raise ErrorDeValidacion(
            f"El parámetro «{clave}» tiene un valor inválido: {parametro.valor!r}"
        ) from exc


def fijar_parametro(
    clave: str,
    valor: Any,
    *,
    tipo_dato: str | None = None,
    descripcion: str = "",
) -> ParametroSistema:
    """Crea o actualiza un parámetro del sistema.

    El usuario que realiza el cambio no se recibe como argumento: la auditoría lo toma del
    contexto de la petición (:mod:`apps.auditoria.context`), de modo que quede registrado
    incluso si el llamador lo olvida.

    Args:
        clave: Clave única del parámetro.
        valor: Valor que se almacenará como texto.
        tipo_dato: Tipo de dato; si se omite, se conserva el actual.
        descripcion: Texto explicativo para la interfaz.

    Returns:
        El parámetro guardado.

    Raises:
        ErrorDeValidacion: si el valor no corresponde al tipo indicado.
    """
    with transaction.atomic():
        parametro, _ = ParametroSistema.objects.select_for_update().get_or_create(
            clave=clave,
            defaults={
                "tipo_dato": tipo_dato or ParametroSistema.TipoDato.TEXTO,
                "descripcion": descripcion,
            },
        )
        if tipo_dato:
            parametro.tipo_dato = tipo_dato
        if descripcion:
            parametro.descripcion = descripcion
        try:
            parametro.valor = _CONVERSIONES[parametro.tipo_dato](valor)
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise ErrorDeValidacion(
                f"El valor {valor!r} no corresponde al tipo "
                f"{parametro.get_tipo_dato_display()} del parámetro «{clave}»."
            ) from exc
        parametro.full_clean(exclude=["descripcion"])
        parametro.save()
    return parametro


# --------------------------------------------------------------------------- #
# Secuencias documentales
# --------------------------------------------------------------------------- #
def asegurar_secuencia(
    tipo: str,
    *,
    prefijo: str = "",
    longitud: int = 6,
    sucursal: Sucursal | None = None,
) -> SecuenciaDocumental:
    """Devuelve la secuencia del tipo indicado, creándola si no existe."""
    secuencia, creada = SecuenciaDocumental.objects.get_or_create(
        tipo=tipo,
        sucursal=sucursal,
        defaults={"prefijo": prefijo, "longitud": longitud},
    )
    if creada:
        logger.info("Secuencia documental creada: %s", secuencia)
    return secuencia


def siguiente_numero(tipo: str, *, sucursal: Sucursal | None = None) -> str:
    """Reserva y devuelve el próximo número de una secuencia documental.

    La fila se bloquea con ``select_for_update()`` dentro de una transacción, de modo que
    dos usuarios concurrentes nunca obtienen el mismo número ni se producen huecos.

    Args:
        tipo: Tipo de documento (por ejemplo ``RECIBO_PAGO``).
        sucursal: Sucursal a la que pertenece el consecutivo.

    Returns:
        El número ya formateado, por ejemplo ``REC-000123``.

    Raises:
        ErrorDeConfiguracion: si la secuencia no existe o está inactiva.
    """
    with transaction.atomic():
        try:
            secuencia = (
                SecuenciaDocumental.objects.select_for_update()
                .filter(tipo=tipo, sucursal=sucursal, activa=True)
                .get()
            )
        except SecuenciaDocumental.DoesNotExist as exc:
            raise ErrorDeConfiguracion(
                f"No existe una secuencia activa para «{tipo}». "
                "Créela antes de emitir documentos de este tipo."
            ) from exc

        numero = secuencia.formatear(secuencia.siguiente)
        secuencia.siguiente += 1
        secuencia.save(update_fields=["siguiente", "actualizado_en"])
    return numero


# --------------------------------------------------------------------------- #
# Idempotencia
# --------------------------------------------------------------------------- #
def ejecutar_una_vez[T](
    clave: UUID | str,
    modulo: str,
    operacion: str,
    funcion: Callable[[], T],
) -> T:
    """Ejecuta ``funcion`` una sola vez para la clave indicada.

    Si la clave ya fue registrada, devuelve el resultado anterior sin volver a ejecutar
    la operación. Así un doble clic no duplica un depósito ni un pago.

    Args:
        clave: Identificador único de la operación (lo genera el formulario).
        modulo: Módulo que ejecuta la operación.
        operacion: Nombre de la operación.
        funcion: Callable sin argumentos que realiza el trabajo y devuelve el id resultante.

    Returns:
        El resultado de ``funcion`` (o el ya registrado).

    Raises:
        ErrorDeConcurrencia: si otra petición está ejecutando la misma operación.
    """
    clave_uuid = clave if isinstance(clave, UUID) else UUID(str(clave))
    try:
        with transaction.atomic():
            registro = OperacionIdempotente.objects.create(
                clave=clave_uuid, modulo=modulo, operacion=operacion
            )
            resultado = funcion()
            registro.resultado_id = getattr(resultado, "pk", None) or _a_entero(resultado)
            registro.save(update_fields=["resultado_id"])
            return resultado
    except IntegrityError as exc:
        raise ErrorDeConcurrencia(
            "Esta operación ya fue registrada. Actualice la página para ver el resultado."
        ) from exc


def _a_entero(valor: Any) -> int | None:
    """Convierte el resultado de una operación a entero, si es posible."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def ya_ejecutada(clave: UUID | str) -> bool:
    """Indica si una clave de idempotencia ya fue utilizada."""
    clave_uuid = clave if isinstance(clave, UUID) else UUID(str(clave))
    return OperacionIdempotente.objects.filter(clave=clave_uuid).exists()
