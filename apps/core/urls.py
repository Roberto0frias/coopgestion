"""Rutas del núcleo."""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("parametros/", views.ParametroListView.as_view(), name="parametros"),
    path(
        "parametros/<int:pk>/editar/",
        views.ParametroUpdateView.as_view(),
        name="parametro_editar",
    ),
]
