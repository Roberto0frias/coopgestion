from django.urls import path

from . import views

app_name = "ahorros"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("productos/nuevo/", views.crear_producto, name="crear_producto"),
    path("productos/<int:pk>/editar/", views.editar_producto, name="editar_producto"),
    path("cuentas/abrir/", views.abrir, name="abrir"),
    path("movimientos/", views.movimientos_pendientes, name="movimientos"),
]
