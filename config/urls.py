from apps.core.views import inicio, modulo_pendiente
from apps.usuarios.views import CambioContrasenaView
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "cuentas/ingresar/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("cuentas/salir/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "cuentas/cambiar-contrasena/",
        CambioContrasenaView.as_view(),
        name="password_change",
    ),
    path("", inicio, name="inicio"),
    path("modulo/<slug:modulo>/", modulo_pendiente, name="modulo_pendiente"),
    path("socios/", include("apps.socios.urls")),
    path("ahorros/", include("apps.ahorros.urls")),
    path("contabilidad/", include("apps.contabilidad.urls")),
]
