"""Configuración de la aplicación de usuarios."""

from __future__ import annotations

from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Usuarios internos, roles y control de acceso."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"
    verbose_name = "Usuarios y roles"
