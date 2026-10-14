"""Configuración de la aplicación de auditoría."""

from __future__ import annotations

from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    """Bitácora inmutable con cadena de hash."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditoria"
    verbose_name = "Auditoría"

    def ready(self) -> None:
        """Conecta las señales que registran automáticamente los cambios."""
        from . import signals

        signals.conectar()
