"""Administración de usuarios y roles."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import IntentoAcceso, Rol, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "es_solo_lectura", "orden", "activo", "cantidad_permisos")
    list_filter = ("es_solo_lectura", "activo")
    search_fields = ("codigo", "nombre")
    filter_horizontal = ("permisos",)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administración del usuario personalizado."""

    list_display = (
        "username",
        "nombre_completo",
        "rol",
        "sucursal",
        "is_active",
        "esta_bloqueado",
        "ultimo_acceso",
    )
    list_filter = ("rol", "is_active", "is_staff", "sucursal")
    search_fields = ("username", "email", "nombres", "apellidos", "cedula")
    ordering = ("nombres", "apellidos")
    readonly_fields = (
        "ultimo_acceso",
        "intentos_fallidos",
        "bloqueado_hasta",
        "creado_en",
        "actualizado_en",
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("nombres", "apellidos", "cedula", "email", "telefono")}),
        ("Rol y sucursal", {"fields": ("rol", "sucursal")}),
        (
            "Permisos especiales",
            {"fields": ("is_active", "is_staff", "is_superuser", "debe_cambiar_password")},
        ),
        (
            "Seguridad",
            {"fields": ("ultimo_acceso", "intentos_fallidos", "bloqueado_hasta")},
        ),
        ("Trazabilidad", {"fields": ("creado_en", "actualizado_en")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "nombres",
                    "apellidos",
                    "rol",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(IntentoAcceso)
class IntentoAccesoAdmin(admin.ModelAdmin):
    """Solo lectura: es evidencia de seguridad."""

    list_display = ("fecha", "username_intentado", "exitoso", "motivo_fallo", "ip")
    list_filter = ("exitoso",)
    search_fields = ("username_intentado", "ip")
    date_hierarchy = "fecha"

    def has_add_permission(self, request) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False
