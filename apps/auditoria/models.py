"""Modelo de la bitácora de auditoría.

Cada registro es **inmutable**: no se puede modificar ni eliminar. El campo
``hash_registro`` encadena cada entrada con la anterior mediante SHA-256, de modo que
alterar cualquier registro del historial rompe la cadena y la verificación lo detecta.
"""

from __future__ import annotations

from typing import Any

from apps.core.exceptions import ErrorDeNegocio
from django.db import models
from django.utils import timezone


class RegistroAuditoria(models.Model):
    """Un cambio ocurrido en el sistema: quién, qué, cuándo, desde dónde y qué cambió."""

    class Accion(models.TextChoices):
        CREAR = "CREAR", "Creación"
        ACTUALIZAR = "ACTUALIZAR", "Actualización"
        ELIMINAR = "ELIMINAR", "Eliminación"
        INICIAR_SESION = "INICIAR_SESION", "Inicio de sesión"
        CERRAR_SESION = "CERRAR_SESION", "Cierre de sesión"
        ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado"
        SISTEMA = "SISTEMA", "Proceso del sistema"

    #: Se asigna explícitamente (no con ``auto_now_add``) para que el hash se pueda
    #: calcular antes de guardar y siga siendo verificable después.
    fecha = models.DateTimeField("fecha", default=timezone.now, editable=False, db_index=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registros_auditoria",
    )
    usuario_texto = models.CharField(
        "usuario (texto)",
        max_length=50,
        blank=True,
        help_text="Se conserva aunque el usuario sea eliminado.",
    )
    ip = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    user_agent = models.CharField("navegador", max_length=250, blank=True)
    accion = models.CharField("acción", max_length=20, choices=Accion.choices, db_index=True)
    app = models.CharField("aplicación", max_length=40, blank=True)
    modelo = models.CharField("modelo", max_length=60, blank=True)
    objeto_id = models.CharField("identificador del objeto", max_length=40, blank=True)
    descripcion = models.CharField("descripción", max_length=250, blank=True)
    valores_anteriores = models.JSONField("valores anteriores", null=True, blank=True)
    valores_nuevos = models.JSONField("valores nuevos", null=True, blank=True)
    hash_anterior = models.CharField("hash anterior", max_length=64, blank=True)
    hash_registro = models.CharField("hash del registro", max_length=64, db_index=True)

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ["-id"]
        permissions = [
            ("puede_ver_auditoria", "Puede consultar la bitácora de auditoría"),
            ("puede_verificar_cadena", "Puede verificar la cadena de integridad"),
        ]
        indexes = [
            models.Index(fields=["app", "modelo", "objeto_id"], name="ix_auditoria_objeto"),
            models.Index(fields=["accion", "fecha"], name="ix_auditoria_accion_fecha"),
        ]

    def __str__(self) -> str:
        return f"{self.fecha:%d/%m/%Y %H:%M:%S} · {self.accion} · {self.modelo}#{self.objeto_id}"

    # ------------------------------------------------------------------ #
    # Inmutabilidad
    # ------------------------------------------------------------------ #
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Impide modificar un registro ya guardado.

        Raises:
            ErrorDeNegocio: si se intenta actualizar un registro existente.
        """
        if self.pk is not None:
            raise ErrorDeNegocio(
                "Los registros de auditoría son inmutables: no se pueden modificar. "
                "Si hubo un error, registre la corrección como un nuevo asiento."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """Impide eliminar registros de auditoría.

        Raises:
            ErrorDeNegocio: siempre.
        """
        raise ErrorDeNegocio(
            "Los registros de auditoría no se pueden eliminar: son la evidencia del sistema."
        )

    @property
    def resumen_cambios(self) -> list[dict[str, Any]]:
        """Lista de campos que cambiaron, con su valor anterior y el nuevo."""
        anteriores = self.valores_anteriores or {}
        nuevos = self.valores_nuevos or {}
        claves = sorted(set(anteriores) | set(nuevos))
        cambios = []
        for clave in claves:
            antes = anteriores.get(clave)
            despues = nuevos.get(clave)
            if antes != despues:
                cambios.append({"campo": clave, "antes": antes, "despues": despues})
        return cambios
