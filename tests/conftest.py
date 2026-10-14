"""Configuración común de las pruebas y conexión a PostgreSQL.

Los parámetros de conexión se pueden sobrescribir por variables de entorno con el
prefijo ``COOPGESTION_DB_``. Los valores por defecto corresponden al PostgreSQL 16
portable de desarrollo (puerto 5433).
"""

from __future__ import annotations

import os

import psycopg
import pytest

PARAMETROS_BD: dict[str, object] = {
    "host": os.environ.get("COOPGESTION_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("COOPGESTION_DB_PORT", "5433")),
    "dbname": os.environ.get("COOPGESTION_DB_NAME", "coopgestion"),
    "user": os.environ.get("COOPGESTION_DB_USER", "coopgestion"),
    "password": os.environ.get("COOPGESTION_DB_PASSWORD", "coopgestion_dev"),
}


@pytest.fixture(scope="session")
def parametros_bd() -> dict[str, object]:
    """Parámetros de conexión vigentes, para pruebas que abren conexiones propias."""
    return PARAMETROS_BD


@pytest.fixture(scope="session")
def conexion() -> psycopg.Connection:
    """Conexión de sesión a PostgreSQL, en modo autocommit.

    Si la base no está disponible, las pruebas que la requieren fallan con un mensaje
    accionable en lugar de saltarse silenciosamente: el entorno es parte de lo que se
    verifica. Las pruebas de cálculo puro no piden esta fixture y no dependen de la base.
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
