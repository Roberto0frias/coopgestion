from django.urls import path

from . import views

app_name = "contabilidad"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.crear, name="crear"),
    path("periodos/abrir-actual/", views.abrir_periodo_actual, name="abrir_periodo_actual"),
    path("periodos/<int:periodo_id>/cerrar/", views.cerrar_periodo, name="cerrar_periodo"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/confirmar/", views.confirmar, name="confirmar"),
    path("<int:pk>/solicitar-reverso/", views.solicitar_reverso_view, name="solicitar_reverso"),
    path(
        "reversos/<int:solicitud_id>/resolver/",
        views.resolver_reverso_view,
        name="resolver_reverso",
    ),
]
