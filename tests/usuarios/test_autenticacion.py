"""Pruebas de autenticación: credenciales, bloqueo por intentos y trazabilidad."""

from __future__ import annotations

from datetime import timedelta

import pytest
from apps.core.exceptions import ErrorDeNegocio
from apps.usuarios.models import IntentoAcceso
from apps.usuarios.services import autenticar, desbloquear_usuario
from django.utils import timezone

from tests.conftest import CLAVE_PRUEBA

pytestmark = pytest.mark.django_db


def test_autenticacion_correcta(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "cajero1")

    autenticado = autenticar("cajero1", CLAVE_PRUEBA)

    assert autenticado.pk == usuario.pk
    usuario.refresh_from_db()
    assert usuario.intentos_fallidos == 0
    assert usuario.ultimo_acceso is not None
    assert IntentoAcceso.objects.filter(usuario=usuario, exitoso=True).count() == 1


def test_usuario_inexistente_no_revela_informacion() -> None:
    with pytest.raises(ErrorDeNegocio) as excinfo:
        autenticar("no_existe", "cualquier-clave")

    assert str(excinfo.value) == "Usuario o contraseña incorrectos."
    registro = IntentoAcceso.objects.get()
    assert registro.exitoso is False
    assert registro.motivo_fallo == "usuario inexistente"


def test_contrasena_incorrecta_suma_intento(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "cajero2")

    with pytest.raises(ErrorDeNegocio, match="incorrectos"):
        autenticar("cajero2", "clave-mala")

    usuario.refresh_from_db()
    assert usuario.intentos_fallidos == 1
    assert usuario.bloqueado_hasta is None


def test_bloqueo_tras_cinco_intentos_fallidos(fabrica_usuarios, settings) -> None:
    settings.COOPGESTION = {**settings.COOPGESTION, "INTENTOS_LOGIN": 5, "MINUTOS_BLOQUEO": 15}
    usuario = fabrica_usuarios("CAJERO", "cajero3")

    for _ in range(5):
        with pytest.raises(ErrorDeNegocio):
            autenticar("cajero3", "clave-mala")

    usuario.refresh_from_db()
    assert usuario.intentos_fallidos == 5
    assert usuario.bloqueado_hasta is not None
    assert usuario.esta_bloqueado is True


def test_cuenta_bloqueada_rechaza_incluso_la_clave_correcta(fabrica_usuarios, settings) -> None:
    settings.COOPGESTION = {**settings.COOPGESTION, "INTENTOS_LOGIN": 2, "MINUTOS_BLOQUEO": 15}
    usuario = fabrica_usuarios("CAJERO", "cajero4")

    for _ in range(2):
        with pytest.raises(ErrorDeNegocio):
            autenticar("cajero4", "clave-mala")

    with pytest.raises(ErrorDeNegocio, match="bloqueada"):
        autenticar("cajero4", CLAVE_PRUEBA)

    usuario.refresh_from_db()
    assert usuario.esta_bloqueado is True


def test_bloqueo_expirado_permite_entrar(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "cajero5")
    usuario.intentos_fallidos = 5
    usuario.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

    autenticado = autenticar("cajero5", CLAVE_PRUEBA)

    assert autenticado.pk == usuario.pk
    usuario.refresh_from_db()
    assert usuario.intentos_fallidos == 0
    assert usuario.bloqueado_hasta is None


def test_desbloqueo_manual(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios("CAJERO", "cajero6")
    usuario.intentos_fallidos = 5
    usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

    desbloquear_usuario(usuario)

    usuario.refresh_from_db()
    assert usuario.esta_bloqueado is False
    assert usuario.intentos_fallidos == 0


def test_usuario_inactivo_no_puede_entrar(fabrica_usuarios) -> None:
    fabrica_usuarios("CAJERO", "cajero7", password=CLAVE_PRUEBA)
    from apps.usuarios.models import Usuario

    usuario = Usuario.objects.get(username="cajero7")
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])

    with pytest.raises(ErrorDeNegocio, match="desactivada"):
        autenticar("cajero7", CLAVE_PRUEBA)

    assert IntentoAcceso.objects.filter(motivo_fallo="usuario inactivo").exists()


def test_autenticacion_no_distingue_mayusculas_en_el_usuario(fabrica_usuarios) -> None:
    fabrica_usuarios("CAJERO", "cajero8")

    autenticado = autenticar("CAJERO8", CLAVE_PRUEBA)

    assert autenticado.username == "cajero8"


def test_se_registra_la_ip_del_proxy(fabrica_usuarios) -> None:
    fabrica_usuarios("CAJERO", "cajero9")

    class PeticionFalsa:
        META = {
            "HTTP_X_FORWARDED_FOR": "190.80.10.5, 10.0.0.1",
            "HTTP_USER_AGENT": "NavegadorDePrueba/1.0",
            "REMOTE_ADDR": "10.0.0.1",
        }

    autenticar("cajero9", CLAVE_PRUEBA, request=PeticionFalsa())

    registro = IntentoAcceso.objects.get(exitoso=True)
    assert registro.ip == "190.80.10.5"
    assert registro.user_agent == "NavegadorDePrueba/1.0"
