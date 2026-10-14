"""Administración de la bitácora: solo consulta, nunca edición."""

from __future__ import annotations

from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """La bitácora es evidencia: no se crea, no se edita y no se elimina."""

    list_display = ("fecha", "accion", "app", "modelo", "objeto_id", "usuario_texto", "ip")
    list_filter = ("accion", "app", "modelo")
    search_fields = ("usuario_texto", "descripcion", "objeto_id")
    date_hierarchy = "fecha"
    ordering = ("-id",)
    readonly_fields = (
        "fecha",
        "usuario",
        "usuario_texto",
        "ip",
        "user_agent",
        "accion",
        "app",
        "modelo",
        "objeto_id",
        "descripcion",
        "valores_anteriores",
        "valores_nuevos",
        "hash_anterior",
        "hash_registro",
    )

    def has_add_permission(self, request) -> bool:  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # noqa: ARG002
        return False
