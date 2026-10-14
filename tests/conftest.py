"""Configuración común de las pruebas.

Contiene dos grupos de fixtures:

* Las de infraestructura (``conexion``, ``parametros_bd``) abren conexiones crudas con
  psycopg contra el clúster de desarrollo, para verificar PostgreSQL sin pasar por Django.
* Las de dominio (``roles``, ``fabrica_usuarios``, ``cliente_*``) usan la base de datos de
  pruebas de Django y crean usuarios con cada rol para verificar la matriz de permisos.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from io import StringIO
from typing import Any

import psycopg
import pytest
from django.core.management import call_command

PARAMETROS_BD: dict[str, object] = {
    "host": os.environ.get("COOPGESTION_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("COOPGESTION_DB_PORT", "5433")),
    "dbname": os.environ.get("COOPGESTION_DB_NAME", "coopgestion"),
    "user": os.environ.get("COOPGESTION_DB_USER", "coopgestion"),
    "password": os.environ.get("COOPGESTION_DB_PASSWORD", "coopgestion_dev"),
}

#: Contraseña que cumple la política de 12 caracteres mínimo, sin ser común.
CLAVE_PRUEBA = "ClaveDePrueba2026!"


# --------------------------------------------------------------------------- #
# Infraestructura (conexión cruda a PostgreSQL)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def parametros_bd() -> dict[str, object]:
    """Parámetros de conexión vigentes, para pruebas que abren conexiones propias."""
    return PARAMETROS_BD


@pytest.fixture(scope="session")
def conexion() -> Iterator[psycopg.Connection]:
    """Conexión de sesión a PostgreSQL, en modo autocommit.

    Si la base no está disponible, las pruebas que la requieren fallan con un mensaje
    accionable en lugar de saltarse silenciosamente. Las pruebas de cálculo puro no piden
    esta fixture y no dependen de la base.
    """
    try:
        conn = psycopg.connect(**PARAMETROS_BD, autocommit=True)  # type: ignore[arg-type]
    except psycopg.OperationalError as exc:
        pytest.fail(
            "No se pudo conectar a PostgreSQL en "
            f"{PARAMETROS_BD['host']}:{PARAMETROS_BD['port']} "
            f"(base {PARAMETROS_BD['dbname']}, usuario {PARAMETROS_BD['user']}).\n"
            "Arranque el servidor local con: powershell -File scripts\\entorno\\pg_start.ps1\n"
            f"Detalle: {exc}",
            pytrace=False,
        )
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS pruebas")
    yield conn
    conn.close()


# --------------------------------------------------------------------------- #
# Dominio (base de datos de pruebas de Django)
# --------------------------------------------------------------------------- #
@pytest.fixture
def sucursal(db) -> Any:
    """Sucursal central de prueba."""
    from apps.core.models import Sucursal

    return Sucursal.objects.create(codigo="CEN", nombre="Sucursal Central")


@pytest.fixture
def roles(db) -> dict[str, Any]:
    """Aplica la matriz de roles y devuelve los roles indexados por código."""
    from apps.usuarios.models import Rol

    call_command("sembrar_roles", stdout=StringIO())
    return {rol.codigo: rol for rol in Rol.objects.all()}


@pytest.fixture
def fabrica_usuarios(roles: dict[str, Any], sucursal: Any) -> Callable[..., Any]:
    """Devuelve una función para crear usuarios con un rol concreto."""
    from apps.usuarios.services import crear_usuario

    def _crear(
        codigo_rol: str,
        username: str | None = None,
        *,
        password: str | None = CLAVE_PRUEBA,
        **extra: Any,
    ) -> Any:
        nombre_usuario = username or f"usuario_{codigo_rol.lower()}"
        return crear_usuario(
            username=nombre_usuario,
            email=f"{nombre_usuario}@coopgestion.local",
            nombres="Persona",
            apellidos=codigo_rol.title(),
            rol=roles[codigo_rol],
            password=password,
            sucursal=sucursal,
            **extra,
        )

    return _crear


@pytest.fixture
def usuario_admin(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("ADMIN", "admin")


@pytest.fixture
def usuario_contador(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("CONTADOR")


@pytest.fixture
def usuario_oficial(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("OFICIAL")


@pytest.fixture
def usuario_cajero(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("CAJERO")


@pytest.fixture
def usuario_auditor(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("AUDITOR")


@pytest.fixture
def usuario_comite(fabrica_usuarios: Callable[..., Any]) -> Any:
    return fabrica_usuarios("COMITE")


def _autenticar(client: Any, usuario: Any) -> Any:
    client.force_login(usuario)
    return client


@pytest.fixture
def cliente_admin(client, usuario_admin) -> Any:
    return _autenticar(client, usuario_admin)


@pytest.fixture
def cliente_cajero(client, usuario_cajero) -> Any:
    return _autenticar(client, usuario_cajero)


@pytest.fixture
def cliente_oficial(client, usuario_oficial) -> Any:
    return _autenticar(client, usuario_oficial)


@pytest.fixture
def cliente_auditor(client, usuario_auditor) -> Any:
    return _autenticar(client, usuario_auditor)


@pytest.fixture
def cliente_contador(client, usuario_contador) -> Any:
    return _autenticar(client, usuario_contador)


@pytest.fixture
def cliente_comite(client, usuario_comite) -> Any:
    return _autenticar(client, usuario_comite)
