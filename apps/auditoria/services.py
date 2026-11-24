"""Escritura serializada y encadenada de eventos de auditoría."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from .models import EstadoCadena, EventoAuditoria


def registrar_evento(
    *,
    accion: str,
    usuario=None,
    request=None,
    objeto=None,
    detalle: dict[str, Any] | None = None,
) -> EventoAuditoria:
    """Agrega un evento a la cadena con bloqueo transaccional."""
    with transaction.atomic():
        estado, _ = EstadoCadena.objects.get_or_create(pk=1)
        estado = EstadoCadena.objects.select_for_update().get(pk=estado.pk)
        anterior = estado.ultimo_hash
        fecha = timezone.now()
        app = objeto._meta.app_label if objeto is not None and hasattr(objeto, "_meta") else ""
        modelo = objeto._meta.model_name if objeto is not None and hasattr(objeto, "_meta") else ""
        objeto_id = str(objeto.pk) if objeto is not None and getattr(objeto, "pk", None) else ""
        ip = None
        agente = ""
        if request is not None:
            # REMOTE_ADDR evita que una petición falsifique HTTP_X_FORWARDED_FOR.
            direccion = request.META.get("REMOTE_ADDR")
            try:
                ip = str(ipaddress.ip_address(direccion)) if direccion else None
            except ValueError:
                ip = None
            agente = request.META.get("HTTP_USER_AGENT", "")[:512]
        detalle_normalizado = json.loads(
            json.dumps(detalle or {}, cls=DjangoJSONEncoder, ensure_ascii=False)
        )
        cuerpo = {
            "accion": accion,
            "usuario_id": getattr(usuario, "pk", None),
            "fecha": fecha.isoformat(),
            "app": app,
            "modelo": modelo,
            "objeto_id": objeto_id,
            "detalle": detalle_normalizado,
            "ip": ip,
            "user_agent": agente,
        }
        serializado = json.dumps(cuerpo, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{anterior}{serializado}".encode()).hexdigest()
        evento = EventoAuditoria.objects.create(
            usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
            fecha=fecha,
            accion=accion,
            app=app,
            modelo=modelo,
            objeto_id=objeto_id,
            ip=ip,
            user_agent=agente,
            detalle=detalle_normalizado,
            hash_anterior=anterior,
            hash_registro=digest,
        )
        estado.ultimo_hash = digest
        EstadoCadena.objects.filter(pk=estado.pk).update(ultimo_hash=digest)
        return evento


def verificar_cadena() -> tuple[bool, int | None]:
    """Comprueba hashes y enlaces cronológicos; devuelve (válida, id con error)."""
    anterior = ""
    for evento in EventoAuditoria.objects.order_by("id").iterator():
        cuerpo = {
            "accion": evento.accion,
            "usuario_id": evento.usuario_id,
            "fecha": evento.fecha.isoformat(),
            "app": evento.app,
            "modelo": evento.modelo,
            "objeto_id": evento.objeto_id,
            "detalle": evento.detalle,
            "ip": str(evento.ip) if evento.ip else None,
            "user_agent": evento.user_agent,
        }
        serializado = json.dumps(cuerpo, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{anterior}{serializado}".encode()).hexdigest()
        if evento.hash_anterior != anterior or evento.hash_registro != digest:
            return False, evento.pk
        anterior = digest
    estado = EstadoCadena.objects.filter(pk=1).first()
    if estado and estado.ultimo_hash != anterior:
        return False, None
    return True, None
