"""Registro en el panel de administración de Django."""

from __future__ import annotations

from django.contrib import admin

from .models import (
    Feriado,
    Moneda,
    OperacionIdempotente,
    ParametroSistema,
    SecuenciaDocumental,
    Sucursal,
)


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "telefono", "activa")
    list_filter = ("activa",)
    search_fields = ("codigo", "nombre")


@admin.register(Moneda)
class MonedaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "simbolo", "decimales", "activa")


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "descripcion")
    ordering = ("-fecha",)


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ("clave", "valor", "tipo_dato", "editable")
    list_filter = ("tipo_dato", "editable")
    search_fields = ("clave", "descripcion")


@admin.register(SecuenciaDocumental)
class SecuenciaDocumentalAdmin(admin.ModelAdmin):
    list_display = ("tipo", "prefijo", "siguiente", "longitud", "sucursal", "activa")
    list_filter = ("activa", "tipo")
    search_fields = ("tipo", "prefijo")


@admin.register(OperacionIdempotente)
class OperacionIdempotenteAdmin(admin.ModelAdmin):
    """Solo lectura: es un registro técnico, no un dato editable."""

    list_display = ("clave", "modulo", "operacion", "resultado_id", "creado_en")
    list_filter = ("modulo", "operacion")
    search_fields = ("clave",)
    readonly_fields = ("clave", "modulo", "operacion", "resultado_id", "creado_en")

    def has_add_permission(self, request) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False
