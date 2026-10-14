"""Rutas de autenticación: inicio y cierre de sesión y cambio de contraseña."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("login/", views.InicioSesionView.as_view(), name="login"),
    path("logout/", views.CerrarSesionView.as_view(), name="logout"),
    path("password/", views.CambioPasswordView.as_view(), name="password"),
]
