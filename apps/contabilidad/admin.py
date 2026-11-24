from django.contrib import admin

from apps.auditoria.services import registrar_evento
from apps.usuarios.models import Usuario

from .models import Asiento, CuentaContable, PeriodoContable


class AccesoContableMixin:
    def _puede_leer(self, request):
        return request.user.is_superuser or request.user.rol in (
            Usuario.Rol.ADMIN,
            Usuario.Rol.CONTADOR,
            Usuario.Rol.AUDITOR,
        )

    def _puede_editar(self, request):
        return request.user.is_superuser or request.user.rol in (
            Usuario.Rol.ADMIN,
            Usuario.Rol.CONTADOR,
        )

    def has_module_permission(self, request):
        return self._puede_leer(request)

    def has_view_permission(self, request, obj=None):
        del obj
        return self._puede_leer(request)


@admin.register(CuentaContable)
class CuentaContableAdmin(AccesoContableMixin, admin.ModelAdmin):
    list_display = ("codigo", "nombre", "grupo", "naturaleza", "nivel", "activa")
    list_filter = ("grupo", "naturaleza", "activa", "permite_movimiento")
    search_fields = ("codigo", "nombre")
    readonly_fields = ("codigo", "grupo", "naturaleza", "nivel", "cuenta_padre", "es_efectivo")

    def get_readonly_fields(self, request, obj=None):
        del request
        return self.readonly_fields if obj else ()

    def has_add_permission(self, request):
        return self._puede_editar(request)

    def has_change_permission(self, request, obj=None):
        del obj
        return self._puede_editar(request)

    def has_delete_permission(self, request, obj=None):
        del request, obj
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        registrar_evento(
            usuario=request.user,
            accion="CUENTA_CONTABLE_EDITADA" if change else "CUENTA_CONTABLE_CREADA",
            request=request,
            objeto=obj,
            detalle={"codigo": obj.codigo, "campos_modificados": sorted(form.changed_data)},
        )


@admin.register(PeriodoContable)
class PeriodoContableAdmin(AccesoContableMixin, admin.ModelAdmin):
    list_display = ("anio", "mes", "estado", "abierto_en", "cerrado_en", "cerrado_por")
    list_filter = ("estado", "anio")
    readonly_fields = tuple(field.name for field in PeriodoContable._meta.fields)

    def has_add_permission(self, request):
        del request
        return False

    def has_change_permission(self, request, obj=None):
        del request, obj
        return False

    def has_delete_permission(self, request, obj=None):
        del request, obj
        return False


@admin.register(Asiento)
class AsientoAdmin(AccesoContableMixin, admin.ModelAdmin):
    list_display = ("numero", "fecha", "descripcion", "estado", "total_debito", "creado_por")
    list_filter = ("estado", "periodo__anio", "periodo__mes")
    search_fields = ("numero", "descripcion")
    readonly_fields = tuple(field.name for field in Asiento._meta.fields)

    def has_add_permission(self, request):
        del request
        return False

    def has_change_permission(self, request, obj=None):
        del request, obj
        return False

    def has_delete_permission(self, request, obj=None):
        del request, obj
        return False
