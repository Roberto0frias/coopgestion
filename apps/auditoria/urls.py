"""Rutas de auditoría."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "auditoria"

urlpatterns = [
    path("", views.AuditoriaListView.as_view(), name="lista"),
    path("verificar/", views.VerificarCadenaView.as_view(), name="verificar"),
    path("<int:pk>/", views.AuditoriaDetalleView.as_view(), name="detalle"),
]
