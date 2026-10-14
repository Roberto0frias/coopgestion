"""Vistas del núcleo: panel de inicio y parámetros del sistema.

Las vistas son delgadas: no calculan dinero ni aplican reglas de negocio. Solo comprueban
permisos, delegan en los servicios y eligen la plantilla.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, TemplateView, UpdateView

from apps.auditoria.models import RegistroAuditoria

from .forms import ParametroSistemaForm
from .models import ParametroSistema, SecuenciaDocumental, Sucursal


class InicioView(LoginRequiredMixin, TemplateView):
    """Panel de inicio: resumen del estado del sistema y accesos según el rol."""

    template_name = "inicio.html"

    def get_context_data(self, **kwargs):
        from apps.usuarios.models import Rol, Usuario

        contexto = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        contexto.update(
            {
                "total_usuarios": Usuario.objects.count(),
                "usuarios_activos": Usuario.objects.filter(is_active=True).count(),
                "total_roles": Rol.objects.filter(activo=True).count(),
                "total_sucursales": Sucursal.objects.filter(activa=True).count(),
                "total_secuencias": SecuenciaDocumental.objects.filter(activa=True).count(),
                "eventos_hoy": RegistroAuditoria.objects.filter(fecha__date=hoy).count(),
                "ncf_activo": self._ncf_activo(),
            }
        )
        return contexto

    @staticmethod
    def _ncf_activo() -> bool:
        from django.conf import settings

        return bool(settings.COOPGESTION.get("EMISION_NCF_ACTIVA"))


class ParametroListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listado de parámetros del sistema, ordenado por clave."""

    permission_required = "core.puede_gestionar_parametros"
    model = ParametroSistema
    template_name = "core/parametros_lista.html"
    context_object_name = "parametros"
    paginate_by = 25


class ParametroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición de un parámetro del sistema."""

    permission_required = "core.puede_gestionar_parametros"
    model = ParametroSistema
    form_class = ParametroSistemaForm
    template_name = "core/parametro_form.html"
    success_url = reverse_lazy("core:parametros")

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Parámetro «{self.object.clave}» actualizado.")
        return respuesta
