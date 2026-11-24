from django.contrib import admin

from apps.usuarios.models import Usuario

from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "accion", "app", "modelo", "objeto_id")
    list_filter = ("accion", "app", "fecha")
    search_fields = ("usuario__username", "accion", "modelo", "objeto_id")
    readonly_fields = tuple(field.name for field in EventoAuditoria._meta.fields)
    ordering = ("-id",)

    def _puede_consultar(self, request):
        return request.user.is_superuser or request.user.rol in (
            Usuario.Rol.ADMIN,
            Usuario.Rol.AUDITOR,
        )

    def has_module_permission(self, request):
        return self._puede_consultar(request)

    def has_view_permission(self, request, obj=None):
        del obj
        return self._puede_consultar(request)

    def has_add_permission(self, request):
        del request
        return False

    def has_change_permission(self, request, obj=None):
        del request, obj
        return False

    def has_delete_permission(self, request, obj=None):
        del request, obj
        return False
