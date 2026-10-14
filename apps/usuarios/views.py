"""Vistas de usuarios: inicio de sesión, gestión de usuarios y perfiles.

Las vistas no contienen reglas de negocio: validan permisos, delegan en los servicios y
eligen la plantilla.
"""

from __future__ import annotations

from typing import Any

from apps.auditoria.models import RegistroAuditoria
from apps.auditoria.services import registrar
from apps.core.exceptions import ErrorDeNegocio
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from .forms import (
    FormularioCambioPassword,
    FormularioInicioSesion,
    PerfilForm,
    RestablecerPasswordForm,
    UsuarioCrearForm,
    UsuarioEditarForm,
)
from .models import Rol, Usuario
from .services import actualizar_usuario, desbloquear_usuario, restablecer_password


class InicioSesionView(LoginView):
    """Inicio de sesión con bloqueo por intentos fallidos."""

    template_name = "registration/login.html"
    authentication_form = FormularioInicioSesion
    redirect_authenticated_user = True

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        registrar(
            RegistroAuditoria.Accion.INICIAR_SESION,
            app="usuarios",
            modelo="Usuario",
            objeto_id=self.request.user.pk,
            descripcion="Inicio de sesión",
            usuario=self.request.user,
        )
        return respuesta

    def get_success_url(self) -> str:
        """Obliga a cambiar la contraseña cuando el administrador la restableció."""
        if getattr(self.request.user, "debe_cambiar_password", False):
            return reverse("cuentas:password")
        return super().get_success_url()


class CerrarSesionView(LoginRequiredMixin, View):
    """Cierre de sesión por POST (protegido contra CSRF) y su registro en la bitácora."""

    def post(self, request):
        registrar(
            RegistroAuditoria.Accion.CERRAR_SESION,
            app="usuarios",
            modelo="Usuario",
            objeto_id=request.user.pk,
            descripcion="Cierre de sesión",
            usuario=request.user,
        )
        logout(request)
        messages.info(request, "Su sesión ha finalizado correctamente.")
        return redirect("cuentas:login")

    def get(self, request):
        # Un cierre de sesión por GET sería vulnerable a CSRF: se ignora.
        return redirect("core:inicio")


class PerfilView(LoginRequiredMixin, UpdateView):
    """Datos personales del propio usuario."""

    model = Usuario
    form_class = PerfilForm
    template_name = "usuarios/perfil.html"
    success_url = reverse_lazy("usuarios:perfil")

    def get_object(self, queryset=None) -> Usuario:
        return self.request.user

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, "Sus datos fueron actualizados.")
        return respuesta


class CambioPasswordView(LoginRequiredMixin, PasswordChangeView):
    """Cambio de contraseña del propio usuario."""

    form_class = FormularioCambioPassword
    template_name = "usuarios/password.html"
    success_url = reverse_lazy("core:inicio")

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, "Su contraseña fue actualizada.")
        return respuesta


# --------------------------------------------------------------------------- #
# Gestión de usuarios (requiere permiso)
# --------------------------------------------------------------------------- #
class GestionUsuariosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Base común: exige el permiso de gestión de usuarios.

    No se usa ``raise_exception``: así el usuario anónimo es redirigido al login y el
    usuario autenticado sin permiso recibe 403, que es el comportamiento correcto.
    """

    permission_required = "usuarios.puede_gestionar_usuarios"


class UsuarioListView(GestionUsuariosMixin, ListView):
    """Listado de usuarios internos con búsqueda y filtros."""

    model = Usuario
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"
    paginate_by = 25

    def get_queryset(self):
        consulta = Usuario.objects.select_related("rol", "sucursal").order_by(
            "nombres", "apellidos"
        )
        busqueda = self.request.GET.get("q", "").strip()
        if busqueda:
            consulta = consulta.filter(nombres__icontains=busqueda) | consulta.filter(
                apellidos__icontains=busqueda
            )
        rol = self.request.GET.get("rol")
        if rol:
            consulta = consulta.filter(rol__codigo=rol)
        estado = self.request.GET.get("estado")
        if estado == "activos":
            consulta = consulta.filter(is_active=True)
        elif estado == "inactivos":
            consulta = consulta.filter(is_active=False)
        elif estado == "bloqueados":
            from django.utils import timezone

            consulta = consulta.filter(bloqueado_hasta__gt=timezone.now())
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["roles"] = Rol.objects.filter(activo=True)
        contexto["filtros"] = {
            "q": self.request.GET.get("q", ""),
            "rol": self.request.GET.get("rol", ""),
            "estado": self.request.GET.get("estado", ""),
        }
        return contexto


class UsuarioCreateView(GestionUsuariosMixin, View):
    """Alta de usuario. El servicio crea la cuenta y la auditoría registra el cambio."""

    template_name = "usuarios/formulario.html"

    def get(self, request):
        from django.shortcuts import render

        return render(
            request,
            self.template_name,
            {"form": UsuarioCrearForm(), "titulo": "Nuevo usuario", "accion": "crear"},
        )

    def post(self, request):
        from django.shortcuts import render

        formulario = UsuarioCrearForm(request.POST)
        if not formulario.is_valid():
            return render(
                request,
                self.template_name,
                {"form": formulario, "titulo": "Nuevo usuario", "accion": "crear"},
            )
        try:
            usuario = formulario.save()
        except ErrorDeNegocio as exc:
            formulario.add_error(None, str(exc))
            return render(
                request,
                self.template_name,
                {"form": formulario, "titulo": "Nuevo usuario", "accion": "crear"},
            )
        messages.success(
            request,
            f"Usuario «{usuario.username}» creado. Deberá cambiar la contraseña al entrar.",
        )
        return redirect("usuarios:lista")


class UsuarioUpdateView(GestionUsuariosMixin, UpdateView):
    """Edición de un usuario existente."""

    model = Usuario
    form_class = UsuarioEditarForm
    template_name = "usuarios/formulario.html"
    success_url = reverse_lazy("usuarios:lista")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar {self.object.nombre_completo}"
        contexto["accion"] = "editar"
        return contexto

    def form_valid(self, form):
        try:
            actualizar_usuario(
                self.object,
                rol=form.cleaned_data["rol"],
                sucursal=form.cleaned_data.get("sucursal"),
                email=form.cleaned_data["email"],
                nombres=form.cleaned_data["nombres"],
                apellidos=form.cleaned_data["apellidos"],
                cedula=form.cleaned_data.get("cedula") or "",
                telefono=form.cleaned_data.get("telefono", ""),
                is_active=form.cleaned_data["is_active"],
                ejecutado_por=self.request.user,
            )
        except ErrorDeNegocio as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Usuario actualizado.")
        return redirect(self.success_url)


class UsuarioDesbloquearView(GestionUsuariosMixin, View):
    """Levanta el bloqueo por intentos fallidos."""

    def post(self, request, pk: int):
        usuario = get_object_or_404(Usuario, pk=pk)
        desbloquear_usuario(usuario, ejecutado_por=request.user)
        messages.success(request, f"Bloqueo levantado para «{usuario.username}».")
        return redirect("usuarios:lista")


class UsuarioRestablecerPasswordView(GestionUsuariosMixin, View):
    """Restablece la contraseña de otro usuario (requiere permiso específico)."""

    template_name = "usuarios/restablecer_password.html"

    def get(self, request, pk: int):
        from django.shortcuts import render

        usuario = get_object_or_404(Usuario, pk=pk)
        return render(
            request, self.template_name, {"form": RestablecerPasswordForm(), "objetivo": usuario}
        )

    def post(self, request, pk: int):
        from django.shortcuts import render

        usuario = get_object_or_404(Usuario, pk=pk)
        formulario = RestablecerPasswordForm(request.POST)
        if request.user.pk == usuario.pk:
            messages.error(
                request,
                "Para cambiar su propia contraseña use la opción «Cambiar contraseña».",
            )
            return redirect("usuarios:perfil")
        if not request.user.has_perm("usuarios.puede_restablecer_password"):
            messages.error(request, "No tiene permiso para restablecer contraseñas.")
            return redirect("usuarios:lista")
        if not formulario.is_valid():
            return render(request, self.template_name, {"form": formulario, "objetivo": usuario})
        try:
            restablecer_password(
                usuario, formulario.cleaned_data["password1"], ejecutado_por=request.user
            )
        except ErrorDeNegocio as exc:
            formulario.add_error(None, str(exc))
            return render(request, self.template_name, {"form": formulario, "objetivo": usuario})
        messages.success(
            request,
            f"Contraseña restablecida para «{usuario.username}». "
            "Deberá cambiarla en el próximo acceso.",
        )
        return redirect("usuarios:lista")


class RolListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Consulta de los roles y sus permisos (matriz de la Fase 0)."""

    permission_required = "usuarios.puede_gestionar_usuarios"
    model = Rol
    template_name = "usuarios/roles.html"
    context_object_name = "roles"

    def get_queryset(self):
        return Rol.objects.prefetch_related("permisos__content_type").order_by("orden", "codigo")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["total_roles"] = self.get_queryset().count()
        return contexto
