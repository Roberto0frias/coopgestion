from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.auditoria.services import registrar_evento

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email")}),
        ("Acceso COOPGESTION", {"fields": ("rol", "is_active", "is_staff")}),
        (
            "Seguridad",
            {
                "fields": (
                    "debe_cambiar_password",
                    "intentos_fallidos",
                    "bloqueado_hasta",
                    "ultimo_acceso",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2")}),
        ("Información de la cuenta", {"fields": ("email", "rol", "is_staff")}),
    )

    def _es_administrador(self, request):
        return request.user.is_superuser or request.user.rol == Usuario.Rol.ADMIN

    def has_module_permission(self, request):
        return self._es_administrador(request)

    def has_view_permission(self, request, obj=None):
        del obj
        return self._es_administrador(request)

    def has_add_permission(self, request):
        return self._es_administrador(request)

    def has_change_permission(self, request, obj=None):
        del obj
        return self._es_administrador(request)

    def has_delete_permission(self, request, obj=None):
        del request, obj
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        registrar_evento(
            usuario=request.user,
            accion="USUARIO_EDITADO" if change else "USUARIO_CREADO",
            request=request,
            objeto=obj,
            detalle={
                "campos_modificados": sorted(form.changed_data),
                "rol": obj.rol,
            },
        )
