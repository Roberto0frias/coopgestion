"""Configuración de la aplicación núcleo."""

from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Parámetros, secuencias documentales y modelos base compartidos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Núcleo"
