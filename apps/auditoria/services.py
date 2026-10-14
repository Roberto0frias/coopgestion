"""Servicios de auditoría: registro encadenado y verificación de integridad.

El encadenamiento funciona así: cada registro incluye el hash del anterior y su propio
hash, calculado sobre el contenido completo del registro. Si alguien altera una fila de
la tabla, todos los hashes posteriores dejan de coincidir y
:func:`verificar_cadena` señala exactamente dónde se rompió.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import connection, transaction

from .context import contexto_actual
from .models import RegistroAuditoria

logger = logging.getLogger(__name__)

#: Identificador del bloqueo de asesoría que serializa la escritura de la cadena.
CLAVE_BLOQUEO_CADENA = 815_001

#: Campos que nunca deben copiarse a la bitácora.
#: ``password`` por seguridad; ``actualizado_en`` porque cambia en cada guardado y
#: generaría un registro de auditoría sin ningún cambio real de datos.
CAMPOS_EXCLUIDOS = frozenset({"password", "actualizado_en"})


def normalizar(valor: Any) -> Any:  # noqa: PLR0911 - despacho por tipo, un return por caso
    """Convierte un valor a algo serializable en JSON de forma determinista."""
    if valor is None or isinstance(valor, (bool, int, float, str)):
        return valor
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat(timespec="microseconds")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, (list, tuple)):
        return [normalizar(elemento) for elemento in valor]
    if isinstance(valor, dict):
        return {str(clave): normalizar(dato) for clave, dato in valor.items()}
    return str(valor)


def serializar_instancia(instancia: Any) -> dict[str, Any]:
    """Extrae los campos de un modelo como diccionario, sin datos sensibles.

    Args:
        instancia: Instancia de un modelo de Django.

    Returns:
        Diccionario ``{campo: valor}``. Para las claves foráneas se guarda el
        identificador, no el objeto completo.
    """
    datos: dict[str, Any] = {}
    for campo in instancia._meta.concrete_fields:
        if campo.name in CAMPOS_EXCLUIDOS:
            continue
        datos[campo.name] = normalizar(getattr(instancia, campo.attname, None))
    return datos


def contenido_para_hash(registro: RegistroAuditoria) -> dict[str, Any]:
    """Contenido exacto que entra en el hash de un registro.

    Es la única función que define el contenido; la usan tanto el registro como la
    verificación, de modo que no puedan divergir.
    """
    return {
        "fecha": registro.fecha.isoformat(timespec="microseconds"),
        "usuario_texto": registro.usuario_texto,
        "ip": registro.ip,
        "user_agent": registro.user_agent,
        "accion": registro.accion,
        "app": registro.app,
        "modelo": registro.modelo,
        "objeto_id": registro.objeto_id,
        "descripcion": registro.descripcion,
        "valores_anteriores": registro.valores_anteriores,
        "valores_nuevos": registro.valores_nuevos,
    }


def calcular_hash(hash_anterior: str, contenido: dict[str, Any]) -> str:
    """Calcula el hash SHA-256 del registro encadenado con el anterior."""
    carga = json.dumps(
        contenido, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )
    return hashlib.sha256(f"{hash_anterior}{carga}".encode()).hexdigest()


def registrar(
    accion: str,
    *,
    app: str = "",
    modelo: str = "",
    objeto_id: Any = "",
    descripcion: str = "",
    anteriores: dict[str, Any] | None = None,
    nuevos: dict[str, Any] | None = None,
    usuario: Any = None,
    usuario_texto: str = "",
    ip: str | None = None,
    user_agent: str = "",
) -> RegistroAuditoria:
    """Añade una entrada a la bitácora y la encadena con la anterior.

    Args:
        accion: Una de las acciones de :class:`RegistroAuditoria.Accion`.
        app: Aplicación afectada (``usuarios``, ``core``, ``ahorros``…).
        modelo: Nombre del modelo afectado.
        objeto_id: Identificador del objeto afectado.
        descripcion: Texto legible de lo ocurrido.
        anteriores: Valores antes del cambio.
        nuevos: Valores después del cambio.
        usuario: Usuario que realizó la acción; si se omite, se toma del contexto.
        usuario_texto: Nombre de usuario alternativo.
        ip: Dirección IP de origen.
        user_agent: Navegador de origen.

    Returns:
        El registro creado.
    """
    contexto = contexto_actual()
    usuario_final = usuario if usuario is not None else contexto.usuario
    texto_final = usuario_texto or contexto.usuario_texto
    if not texto_final and usuario_final is not None:
        texto_final = getattr(usuario_final, "username", "") or ""

    with transaction.atomic():
        # Bloqueo de asesoría: serializa la escritura de la cadena entre procesos, de
        # modo que dos peticiones simultáneas no calculen el mismo hash anterior.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CLAVE_BLOQUEO_CADENA])

        hash_anterior = (
            RegistroAuditoria.objects.order_by("-id")
            .values_list("hash_registro", flat=True)
            .first()
            or ""
        )
        registro = RegistroAuditoria(
            usuario=usuario_final,
            usuario_texto=texto_final[:50],
            ip=ip or contexto.ip,
            user_agent=(user_agent or contexto.user_agent)[:250],
            accion=accion,
            app=app[:40],
            modelo=modelo[:60],
            objeto_id=str(objeto_id or "")[:40],
            descripcion=descripcion[:250],
            valores_anteriores=anteriores,
            valores_nuevos=nuevos,
            hash_anterior=hash_anterior,
            hash_registro="",
        )
        registro.hash_registro = calcular_hash(hash_anterior, contenido_para_hash(registro))
        registro.save()
    return registro


def verificar_cadena(*, limite: int | None = None) -> dict[str, Any]:
    """Recorre la bitácora y comprueba que la cadena de hash esté intacta.

    Args:
        limite: Cantidad máxima de registros a revisar (los más recientes primero).

    Returns:
        Diccionario con ``integridad`` (bool), ``revisados``, ``primer_error_id`` y
        ``detalle``.
    """
    consulta = RegistroAuditoria.objects.order_by("id")
    anterior = ""
    if limite:
        ultimos = list(
            RegistroAuditoria.objects.order_by("-id").values_list("id", flat=True)[:limite]
        )
        if ultimos:
            consulta = RegistroAuditoria.objects.filter(id__in=ultimos).order_by("id")
            # Para verificar un tramo hay que arrancar con el hash del registro inmediato
            # anterior al tramo; de lo contrario el primer registro parecería roto.
            anterior = (
                RegistroAuditoria.objects.filter(id__lt=min(ultimos))
                .order_by("-id")
                .values_list("hash_registro", flat=True)
                .first()
                or ""
            )

    revisados = 0
    for registro in consulta.iterator(chunk_size=500):
        if registro.hash_anterior != anterior:
            return {
                "integridad": False,
                "revisados": revisados,
                "primer_error_id": registro.pk,
                "detalle": (
                    f"El registro {registro.pk} no apunta al hash del registro anterior. "
                    "La cadena fue alterada o se insertó una fila fuera de orden."
                ),
            }
        esperado = calcular_hash(anterior, contenido_para_hash(registro))
        if esperado != registro.hash_registro:
            return {
                "integridad": False,
                "revisados": revisados,
                "primer_error_id": registro.pk,
                "detalle": (
                    f"El contenido del registro {registro.pk} no coincide con su hash. "
                    "El registro fue modificado después de guardarse."
                ),
            }
        anterior = registro.hash_registro
        revisados += 1

    return {
        "integridad": True,
        "revisados": revisados,
        "primer_error_id": None,
        "detalle": f"La cadena está intacta: {revisados} registro(s) verificados.",
    }
