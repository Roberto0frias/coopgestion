"""Vistas de auditoría: consulta de la bitácora y verificación de la cadena."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.dateparse import parse_date
from django.views.generic import DetailView, ListView, TemplateView

from .models import RegistroAuditoria
from .services import verificar_cadena


class AuditoriaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Bitácora paginada con filtros por acción, modelo, usuario y fechas."""

    permission_required = "auditoria.puede_ver_auditoria"
    model = RegistroAuditoria
    template_name = "auditoria/lista.html"
    context_object_name = "registros"
    paginate_by = 50

    def get_queryset(self):
        consulta = RegistroAuditoria.objects.select_related("usuario").order_by("-id")
        parametros = self.request.GET

        accion = parametros.get("accion")
        if accion:
            consulta = consulta.filter(accion=accion)

        modelo = parametros.get("modelo")
        if modelo:
            consulta = consulta.filter(modelo=modelo)

        usuario = parametros.get("usuario")
        if usuario:
            consulta = consulta.filter(usuario_texto__icontains=usuario.strip())

        desde = parse_date(parametros.get("desde") or "")
        if desde:
            consulta = consulta.filter(fecha__date__gte=desde)

        hasta = parse_date(parametros.get("hasta") or "")
        if hasta:
            consulta = consulta.filter(fecha__date__lte=hasta)

        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["acciones"] = RegistroAuditoria.Accion.choices
        contexto["modelos"] = (
            RegistroAuditoria.objects.exclude(modelo="")
            .values_list("modelo", flat=True)
            .distinct()
            .order_by("modelo")
        )
        contexto["filtros"] = {
            "accion": self.request.GET.get("accion", ""),
            "modelo": self.request.GET.get("modelo", ""),
            "usuario": self.request.GET.get("usuario", ""),
            "desde": self.request.GET.get("desde", ""),
            "hasta": self.request.GET.get("hasta", ""),
        }
        return contexto


class AuditoriaDetalleView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de un registro, con la lista de campos que cambiaron."""

    permission_required = "auditoria.puede_ver_auditoria"
    model = RegistroAuditoria
    template_name = "auditoria/detalle.html"
    context_object_name = "registro"


class VerificarCadenaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Comprueba que ningún registro de la bitácora haya sido alterado."""

    permission_required = "auditoria.puede_verificar_cadena"
    template_name = "auditoria/verificar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["resultado"] = verificar_cadena()
        contexto["total_registros"] = RegistroAuditoria.objects.count()
        return contexto
