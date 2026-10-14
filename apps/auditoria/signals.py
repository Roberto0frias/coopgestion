"""Señales que registran automáticamente los cambios en la bitácora.

Se conectan desde :meth:`apps.auditoria.apps.AuditoriaConfig.ready`.

Durante las migraciones la tabla de auditoría puede no existir todavía; en ese caso el
fallo se registra y se continúa, pero **cualquier otro error se propaga**: en un sistema
financiero no se puede perder un registro de auditoría en silencio.
"""

from __future__ import annotations

import logging
from typing import Any

from django.apps import apps
from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from .models import RegistroAuditoria
from .registry import MODELOS_AUDITADOS
from .services import registrar, serializar_instancia

logger = logging.getLogger(__name__)

#: Nombre del atributo temporal donde se guarda el estado previo a un cambio.
ATRIBUTO_ANTERIOR = "_auditoria_valores_anteriores"


def conectar() -> None:
    """Conecta las señales de los modelos auditados (idempotente)."""
    for etiqueta in MODELOS_AUDITADOS:
        try:
            modelo = apps.get_model(etiqueta)
        except LookupError:  # pragma: no cover - modelo aún no disponible
            logger.warning("Modelo auditado no encontrado: %s", etiqueta)
            continue
        models.signals.pre_save.connect(
            _antes_de_guardar, sender=modelo, dispatch_uid=f"auditoria-pre-{etiqueta}"
        )
        models.signals.post_save.connect(
            _despues_de_guardar, sender=modelo, dispatch_uid=f"auditoria-post-{etiqueta}"
        )
        models.signals.post_delete.connect(
            _despues_de_eliminar, sender=modelo, dispatch_uid=f"auditoria-delete-{etiqueta}"
        )


def _antes_de_guardar(sender: type[models.Model], instance: Any, **kwargs: Any) -> None:
    """Guarda el estado previo de la instancia antes de escribirla."""
    if kwargs.get("raw"):
        return  # carga de datos iniciales: no se audita
    if instance.pk is None:
        setattr(instance, ATRIBUTO_ANTERIOR, None)
        return
    anterior = sender.objects.filter(pk=instance.pk).first()
    setattr(
        instance,
        ATRIBUTO_ANTERIOR,
        serializar_instancia(anterior) if anterior is not None else None,
    )


def _despues_de_guardar(sender: type[models.Model], instance: Any, **kwargs: Any) -> None:
    """Registra la creación o la actualización."""
    if kwargs.get("raw"):
        return
    etiqueta = f"{sender._meta.app_label}.{sender.__name__}"
    nuevos = serializar_instancia(instance)
    anteriores = getattr(instance, ATRIBUTO_ANTERIOR, None)
    setattr(instance, ATRIBUTO_ANTERIOR, None)

    if anteriores is None:
        _registrar_seguro(
            RegistroAuditoria.Accion.CREAR,
            etiqueta,
            instance,
            descripcion=f"Creación de {sender._meta.verbose_name}",
            anteriores=None,
            nuevos=nuevos,
        )
        return

    if anteriores != nuevos:
        _registrar_seguro(
            RegistroAuditoria.Accion.ACTUALIZAR,
            etiqueta,
            instance,
            descripcion=f"Actualización de {sender._meta.verbose_name}",
            anteriores=anteriores,
            nuevos=nuevos,
        )


def _despues_de_eliminar(sender: type[models.Model], instance: Any, **kwargs: Any) -> None:
    """Registra la eliminación con los valores que tenía."""
    etiqueta = f"{sender._meta.app_label}.{sender.__name__}"
    _registrar_seguro(
        RegistroAuditoria.Accion.ELIMINAR,
        etiqueta,
        instance,
        descripcion=f"Eliminación de {sender._meta.verbose_name}",
        anteriores=serializar_instancia(instance),
        nuevos=None,
    )


def _registrar_seguro(
    accion: str,
    etiqueta: str,
    instance: Any,
    *,
    descripcion: str,
    anteriores: dict[str, Any] | None,
    nuevos: dict[str, Any] | None,
) -> None:
    """Registra el cambio, tolerando únicamente la ausencia de la tabla de auditoría."""
    app_label, modelo = etiqueta.split(".", 1)
    try:
        registrar(
            accion,
            app=app_label,
            modelo=modelo,
            objeto_id=instance.pk,
            descripcion=descripcion,
            anteriores=anteriores,
            nuevos=nuevos,
        )
    except (ProgrammingError, OperationalError):
        logger.warning(
            "No se pudo escribir en la auditoría (¿migraciones pendientes?): %s %s",
            accion,
            etiqueta,
        )
