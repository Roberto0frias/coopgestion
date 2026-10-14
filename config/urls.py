"""Rutas raíz del proyecto COOPGESTION."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Autenticación: login, logout y cambio de contraseña
    path("cuentas/", include("apps.usuarios.urls_cuentas")),
    # Panel de inicio y parámetros
    path("", include("apps.core.urls")),
    # Gestión de usuarios y roles
    path("usuarios/", include("apps.usuarios.urls")),
    # Bitácora de auditoría
    path("auditoria/", include("apps.auditoria.urls")),
]

admin.site.site_header = "COOPGESTION · Administración"
admin.site.site_title = "COOPGESTION"
admin.site.index_title = "Panel de administración"
