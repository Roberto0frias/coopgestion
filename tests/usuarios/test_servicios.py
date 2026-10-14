"""Pruebas de los servicios de usuarios: alta, edición y contraseñas."""

from __future__ import annotations

import pytest
from apps.core.exceptions import ErrorDeValidacion
from apps.usuarios.models import Usuario
from apps.usuarios.services import (
    actualizar_usuario,
    cambiar_password,
    crear_usuario,
    restablecer_password,
)

from tests.conftest import CLAVE_PRUEBA

pytestmark = pytest.mark.django_db


def test_alta_de_usuario_normaliza_datos(roles, sucursal) -> None:
    usuario = crear_usuario(
        username="  rperez  ",
        email="RPERez@CoopGestion.Local",
        nombres="  Ramón  ",
        apellidos="  Pérez  ",
        rol=roles["CAJERO"],
        password=CLAVE_PRUEBA,
        sucursal=sucursal,
        cedula="001-1234567-8",
    )

    assert usuario.username == "rperez"
    assert usuario.email == "rperez@coopgestion.local"
    assert usuario.nombres == "Ramón"
    assert usuario.apellidos == "Pérez"
    assert usuario.cedula == "00112345678", "La cédula se guarda sin guiones"
    assert usuario.check_password(CLAVE_PRUEBA)
    assert usuario.debe_cambiar_password is True
    assert usuario.nombre_completo == "Ramón Pérez"


def test_contrasena_debil_es_rechazada(roles) -> None:
    with pytest.raises(ErrorDeValidacion) as excinfo:
        crear_usuario(
            username="debil",
            email="debil@coopgestion.local",
            nombres="Clave",
            apellidos="Débil",
            rol=roles["CAJERO"],
            password="123456",
        )
    assert "12" in str(excinfo.value) or "corta" in str(excinfo.value).lower()


def test_usuario_sin_contrasena_queda_inutilizable(roles) -> None:
    usuario = crear_usuario(
        username="sinclave",
        email="sinclave@coopgestion.local",
        nombres="Sin",
        apellidos="Clave",
        rol=roles["CAJERO"],
        password=None,
    )
    assert usuario.has_usable_password() is False


def test_username_y_correo_son_unicos(roles) -> None:
    crear_usuario(
        username="unico",
        email="unico@coopgestion.local",
        nombres="A",
        apellidos="B",
        rol=roles["CAJERO"],
        password=CLAVE_PRUEBA,
    )
    with pytest.raises(Exception):  # noqa: B017 - IntegrityError de la base de datos
        crear_usuario(
            username="unico",
            email="otro@coopgestion.local",
            nombres="C",
            apellidos="D",
            rol=roles["CAJERO"],
            password=CLAVE_PRUEBA,
        )


def test_actualizar_usuario_cambia_solo_lo_indicado(roles, fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "cambios")
    correo_original = usuario.email

    actualizar_usuario(usuario, nombres="Nombre Nuevo")

    usuario.refresh_from_db()
    assert usuario.nombres == "Nombre Nuevo"
    assert usuario.email == correo_original
    assert usuario.rol.codigo == "CAJERO"


def test_no_puede_desactivarse_a_si_mismo(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("ADMIN", "admin2")

    with pytest.raises(ErrorDeValidacion, match="propio usuario"):
        actualizar_usuario(usuario, is_active=False, ejecutado_por=usuario)


def test_cambio_de_contrasena_limpia_bloqueo(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "clave1")
    usuario.intentos_fallidos = 3
    usuario.save(update_fields=["intentos_fallidos"])

    cambiar_password(usuario, "OtraClaveSegura2026!")

    usuario.refresh_from_db()
    assert usuario.check_password("OtraClaveSegura2026!")
    assert usuario.intentos_fallidos == 0
    assert usuario.debe_cambiar_password is False


def test_restablecer_contrasena_exige_cambio_y_no_permite_la_propia(fabrica_usuarios) -> None:
    administrador = fabrica_usuarios("ADMIN", "admin3")
    cajero = fabrica_usuarios("CAJERO", "cajero10", debe_cambiar_password=False)

    restablecer_password(cajero, "TemporalSegura2026!", ejecutado_por=administrador)

    cajero.refresh_from_db()
    assert cajero.check_password("TemporalSegura2026!")
    assert cajero.debe_cambiar_password is True

    with pytest.raises(ErrorDeValidacion, match="propia contraseña"):
        restablecer_password(administrador, "OtraTemporal2026!", ejecutado_por=administrador)


def test_crear_superusuario_no_requiere_rol() -> None:
    superusuario = Usuario.objects.create_superuser(
        username="root", email="root@coopgestion.local", password=CLAVE_PRUEBA
    )
    assert superusuario.is_superuser is True
    assert superusuario.is_staff is True
    assert superusuario.rol is None
    assert superusuario.has_perm("usuarios.puede_gestionar_usuarios") is True
