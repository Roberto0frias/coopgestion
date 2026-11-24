"""Casos de uso del expediente de socios."""

from __future__ import annotations

from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auditoria.services import registrar_evento
from apps.usuarios.models import Usuario

from .models import Socio

ROLES_LECTURA = tuple(Usuario.Rol.values)
ROLES_EDICION = (Usuario.Rol.ADMIN, Usuario.Rol.OFICIAL)
ROLES_ADMISION = (Usuario.Rol.ADMIN, Usuario.Rol.COMITE)


def _exigir_rol(usuario, roles: tuple[str, ...]) -> None:
    if not usuario.is_authenticated or not usuario.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no permite realizar esta acción.")


@transaction.atomic
def registrar_socio(*, datos: dict, usuario: Usuario, request=None) -> Socio:
    _exigir_rol(usuario, ROLES_EDICION)
    socio = Socio(**datos, creado_por=usuario)
    socio.codigo = f"P{uuid4().hex[:15]}"
    socio.full_clean(exclude=["codigo"])
    socio.save()
    socio.codigo = f"SOC-{socio.pk:06d}"
    socio.save(update_fields=["codigo"])
    registrar_evento(
        usuario=usuario,
        accion="SOCIO_REGISTRADO",
        request=request,
        objeto=socio,
        detalle={"codigo": socio.codigo},
    )
    return socio


@transaction.atomic
def editar_socio(*, socio_id: int, datos: dict, usuario: Usuario, request=None) -> Socio:
    _exigir_rol(usuario, ROLES_EDICION)
    socio = Socio.objects.select_for_update().get(pk=socio_id)
    if socio.estado in (Socio.Estado.RECHAZADO, Socio.Estado.RETIRADO):
        raise ValidationError("No se puede editar un expediente rechazado o retirado.")
    campos = []
    for campo, valor in datos.items():
        if getattr(socio, campo) != valor:
            setattr(socio, campo, valor)
            campos.append(campo)
    socio.full_clean(exclude=["codigo"])
    socio.save(update_fields=[*campos, "cedula"] if "cedula" in campos else campos or None)
    if campos:
        registrar_evento(
            usuario=usuario,
            accion="SOCIO_EDITADO",
            request=request,
            objeto=socio,
            detalle={"campos_modificados": sorted(campos)},
        )
    return socio


@transaction.atomic
def aprobar_admision(*, socio_id: int, usuario: Usuario, request=None) -> Socio:
    _exigir_rol(usuario, ROLES_ADMISION)
    socio = Socio.objects.select_for_update().get(pk=socio_id)
    if socio.estado != Socio.Estado.PENDIENTE:
        raise ValidationError("Solo se pueden aprobar expedientes pendientes.")
    if socio.creado_por_id == usuario.pk:
        raise PermissionDenied(
            "La admisión debe aprobarla una persona distinta de quien registró al socio."
        )
    socio.estado = Socio.Estado.ACTIVO
    socio.aprobado_por = usuario
    socio.aprobado_en = timezone.now()
    socio.full_clean(exclude=["codigo"])
    socio.save(update_fields=["estado", "aprobado_por", "aprobado_en"])
    registrar_evento(
        usuario=usuario,
        accion="SOCIO_ADMITIDO",
        request=request,
        objeto=socio,
        detalle={"codigo": socio.codigo, "registrado_por_id": socio.creado_por_id},
    )
    return socio


@transaction.atomic
def rechazar_admision(*, socio_id: int, motivo: str, usuario: Usuario, request=None) -> Socio:
    _exigir_rol(usuario, ROLES_ADMISION)
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError({"motivo": "Indica el motivo del rechazo."})
    socio = Socio.objects.select_for_update().get(pk=socio_id)
    if socio.estado != Socio.Estado.PENDIENTE:
        raise ValidationError("Solo se pueden rechazar expedientes pendientes.")
    if socio.creado_por_id == usuario.pk:
        raise PermissionDenied(
            "La decisión debe tomarla una persona distinta de quien registró al socio."
        )
    socio.estado = Socio.Estado.RECHAZADO
    socio.aprobado_por = usuario
    socio.aprobado_en = timezone.now()
    socio.motivo_rechazo = motivo
    socio.save(update_fields=["estado", "aprobado_por", "aprobado_en", "motivo_rechazo"])
    registrar_evento(
        usuario=usuario,
        accion="ADMISION_SOCIO_RECHAZADA",
        request=request,
        objeto=socio,
        detalle={"codigo": socio.codigo, "motivo": motivo},
    )
    return socio
