"""Pruebas de extremo a extremo de las vistas: accesos, permisos y navegación.

Se verifica lo permitido y lo **denegado**: cada ruta protegida debe rechazar a quien no
tiene el permiso correspondiente.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from tests.conftest import CLAVE_PRUEBA

pytestmark = pytest.mark.django_db

RUTAS_PROTEGIDAS = [
    "/",
    "/usuarios/",
    "/usuarios/roles/",
    "/parametros/",
    "/auditoria/",
    "/auditoria/verificar/",
]


# --------------------------------------------------------------------------- #
# Acceso anónimo
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("ruta", RUTAS_PROTEGIDAS)
def test_usuario_anonimo_es_enviado_al_login(client, ruta: str) -> None:
    respuesta = client.get(ruta)
    assert respuesta.status_code == 302
    assert "/cuentas/login/" in respuesta["Location"]


def test_la_pagina_de_login_es_publica(client) -> None:
    respuesta = client.get("/cuentas/login/")
    assert respuesta.status_code == 200
    assert "COOPGESTION" in respuesta.content.decode()


# --------------------------------------------------------------------------- #
# Inicio y cierre de sesión
# --------------------------------------------------------------------------- #
def test_inicio_de_sesion_exitoso_obliga_a_cambiar_la_contrasena(client, fabrica_usuarios) -> None:
    fabrica_usuarios("CAJERO", "login1", debe_cambiar_password=True)

    respuesta = client.post("/cuentas/login/", {"username": "login1", "password": CLAVE_PRUEBA})

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/cuentas/password/"


def test_inicio_de_sesion_con_clave_incorrecta_muestra_error(client, fabrica_usuarios) -> None:
    fabrica_usuarios("CAJERO", "login2")

    respuesta = client.post("/cuentas/login/", {"username": "login2", "password": "mala"})

    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos." in respuesta.content.decode()


def test_el_inicio_de_sesion_queda_auditado(client, fabrica_usuarios) -> None:
    from apps.auditoria.models import RegistroAuditoria

    fabrica_usuarios("CAJERO", "login3")
    client.post("/cuentas/login/", {"username": "login3", "password": CLAVE_PRUEBA})

    assert RegistroAuditoria.objects.filter(
        accion=RegistroAuditoria.Accion.INICIAR_SESION, usuario_texto="login3"
    ).exists()


def test_el_cierre_de_sesion_requiere_post(cliente_cajero) -> None:
    from django.urls import reverse as reverse_

    respuesta = cliente_cajero.post(reverse_("cuentas:logout"))
    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/cuentas/login/"


def test_el_cierre_de_sesion_por_get_no_cierra_la_sesion(cliente_cajero) -> None:
    respuesta = cliente_cajero.get(reverse("cuentas:logout"))
    assert respuesta.status_code == 302
    # La sesión sigue activa: una petición GET no puede cerrar sesión (protección CSRF).
    assert cliente_cajero.get("/").status_code == 200


# --------------------------------------------------------------------------- #
# Permisos por rol
# --------------------------------------------------------------------------- #
def test_administrador_entra_al_panel_de_inicio(cliente_admin) -> None:
    respuesta = cliente_admin.get("/")
    assert respuesta.status_code == 200
    assert "Panel de inicio" in respuesta.content.decode()


def test_administrador_gestiona_usuarios(cliente_admin) -> None:
    assert cliente_admin.get("/usuarios/").status_code == 200
    assert cliente_admin.get("/usuarios/roles/").status_code == 200
    assert cliente_admin.get("/parametros/").status_code == 200
    assert cliente_admin.get("/auditoria/").status_code == 200
    assert cliente_admin.get("/auditoria/verificar/").status_code == 200


@pytest.mark.parametrize(
    ("fixture_cliente", "ruta"),
    [
        ("cliente_cajero", "/usuarios/"),
        ("cliente_cajero", "/usuarios/roles/"),
        ("cliente_cajero", "/parametros/"),
        ("cliente_cajero", "/auditoria/"),
        ("cliente_oficial", "/usuarios/"),
        ("cliente_comite", "/usuarios/"),
        ("cliente_comite", "/parametros/"),
        ("cliente_contador", "/usuarios/"),
        ("cliente_contador", "/parametros/"),
    ],
)
def test_rutas_denegadas_por_rol(request, fixture_cliente: str, ruta: str) -> None:
    cliente = request.getfixturevalue(fixture_cliente)
    assert cliente.get(ruta).status_code == 403


def test_auditor_puede_ver_pero_no_gestionar(cliente_auditor) -> None:
    assert cliente_auditor.get("/usuarios/").status_code == 403
    assert cliente_auditor.get("/auditoria/").status_code == 200
    assert cliente_auditor.get("/auditoria/verificar/").status_code == 200


def test_contador_ve_auditoria_pero_no_verifica_cadena(cliente_contador) -> None:
    assert cliente_contador.get("/auditoria/").status_code == 200
    assert cliente_contador.get("/auditoria/verificar/").status_code == 403


# --------------------------------------------------------------------------- #
# Navegación por rol y aviso fiscal
# --------------------------------------------------------------------------- #
def test_el_menu_muestra_solo_lo_permitido(client, usuario_cajero, usuario_admin) -> None:
    """El menú se construye a partir de permisos, no de listas de roles.

    Se comprueban los enlaces de navegación, no el texto libre de la página, y se reutiliza
    el mismo cliente cambiando de usuario: dos fixtures de cliente compartirían el mismo
    objeto y la segunda sesión pisaría a la primera.
    """
    client.force_login(usuario_cajero)
    menu_cajero = client.get("/").content.decode()
    assert 'href="/"' in menu_cajero
    assert 'href="/usuarios/"' not in menu_cajero
    assert 'href="/usuarios/roles/"' not in menu_cajero
    assert 'href="/auditoria/"' not in menu_cajero
    assert 'href="/parametros/"' not in menu_cajero

    client.force_login(usuario_admin)
    menu_admin = client.get("/").content.decode()
    assert 'href="/usuarios/"' in menu_admin
    assert 'href="/usuarios/roles/"' in menu_admin
    assert 'href="/auditoria/"' in menu_admin
    assert 'href="/parametros/"' in menu_admin


def test_el_inicio_avisa_que_el_ncf_esta_desactivado(cliente_admin) -> None:
    contenido = cliente_admin.get("/").content.decode()
    assert "NCF" in contenido or "comprobantes fiscales" in contenido
    assert "desactivada" in contenido


def test_perfil_y_cambio_de_contrasena(cliente_cajero) -> None:
    assert cliente_cajero.get("/usuarios/perfil/").status_code == 200
    assert cliente_cajero.get("/cuentas/password/").status_code == 200


def test_el_listado_de_usuarios_filtra_por_rol(cliente_admin) -> None:
    respuesta = cliente_admin.get("/usuarios/", {"rol": "CAJERO"})
    assert respuesta.status_code == 200


def test_la_auditoria_admite_peticiones_htmx(cliente_admin) -> None:
    respuesta = cliente_admin.get(
        "/auditoria/", {"accion": "CREAR"}, headers={"hx-request": "true"}
    )
    assert respuesta.status_code == 200
    assert "tabla-auditoria" in respuesta.content.decode()


def test_el_administrador_puede_crear_un_usuario(cliente_admin, roles) -> None:
    respuesta = cliente_admin.post(
        "/usuarios/nuevo/",
        {
            "username": "nuevo_cajero",
            "email": "nuevo_cajero@coopgestion.local",
            "nombres": "Nuevo",
            "apellidos": "Cajero",
            "cedula": "",
            "telefono": "809-555-0000",
            "rol": roles["CAJERO"].pk,
            "sucursal": "",
            "password1": CLAVE_PRUEBA,
            "password2": CLAVE_PRUEBA,
        },
    )
    assert respuesta.status_code == 302

    from apps.usuarios.models import Usuario

    creado = Usuario.objects.get(username="nuevo_cajero")
    assert creado.rol.codigo == "CAJERO"
    assert creado.debe_cambiar_password is True
