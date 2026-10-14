"""Rutas de gestión de usuarios, perfiles y roles."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="lista"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/desbloquear/", views.UsuarioDesbloquearView.as_view(), name="desbloquear"),
    path(
        "<int:pk>/restablecer-password/",
        views.UsuarioRestablecerPasswordView.as_view(),
        name="restablecer_password",
    ),
    path("roles/", views.RolListView.as_view(), name="roles"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("perfil/password/", views.CambioPasswordView.as_view(), name="perfil_password"),
]
