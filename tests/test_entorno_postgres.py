"""Pruebas de la infraestructura: PostgreSQL 16, precisión NUMERIC y bloqueo de filas.

Estas pruebas verifican que el entorno soporta las garantías que exige la integridad
financiera del sistema: aritmética exacta, aislamiento entre usuarios concurrentes y
principio de menor privilegio.
"""

from __future__ import annotations

from decimal import Decimal

import psycopg
import pytest

pytestmark = pytest.mark.entorno


def test_servidor_es_postgresql_16(conexion: psycopg.Connection) -> None:
    with conexion.cursor() as cur:
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
    assert version.startswith("16."), f"Se esperaba PostgreSQL 16 y se obtuvo {version}"


def test_codificacion_utf8(conexion: psycopg.Connection) -> None:
    with conexion.cursor() as cur:
        cur.execute("SHOW server_encoding")
        codificacion = cur.fetchone()[0]
    assert codificacion == "UTF8", f"Se esperaba UTF8 y se obtuvo {codificacion}"


def test_zona_horaria_por_defecto(conexion: psycopg.Connection) -> None:
    with conexion.cursor() as cur:
        cur.execute("SHOW TimeZone")
        zona = cur.fetchone()[0]
    assert isinstance(zona, str) and zona, "La zona horaria del servidor no está definida"


def test_numeric_no_pierde_centavos(conexion: psycopg.Connection) -> None:
    """La prueba clásica: 0.10 + 0.20 + 1,234,567.89 debe ser exacto."""
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS pruebas.monto")
        cur.execute("CREATE TABLE pruebas.monto (v numeric(18,2) NOT NULL)")
        cur.executemany(
            "INSERT INTO pruebas.monto (v) VALUES (%s)",
            [(Decimal("0.10"),), (Decimal("0.20"),), (Decimal("1234567.89"),)],
        )
        cur.execute("SELECT sum(v) FROM pruebas.monto")
        total = cur.fetchone()[0]
    assert isinstance(total, Decimal)
    assert total == Decimal("1234568.19")


def test_numeric_rechaza_exceso_de_decimales(conexion: psycopg.Connection) -> None:
    """NUMERIC(18,2) redondea a 2 decimales: nunca almacena fracciones de centavo."""
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS pruebas.monto_redondeo")
        cur.execute("CREATE TABLE pruebas.monto_redondeo (v numeric(18,2) NOT NULL)")
        cur.execute("INSERT INTO pruebas.monto_redondeo (v) VALUES (%s)", (Decimal("1.005"),))
        cur.execute("SELECT v FROM pruebas.monto_redondeo")
        valor = cur.fetchone()[0]
    assert valor == Decimal("1.01")


def test_select_for_update_bloquea_filas(
    conexion: psycopg.Connection, parametros_bd: dict[str, object]
) -> None:
    """El bloqueo de filas debe impedir que dos cajeros muevan el mismo saldo a la vez."""
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS pruebas.cuenta")
        cur.execute(
            "CREATE TABLE pruebas.cuenta (id int PRIMARY KEY, saldo numeric(18,2) NOT NULL)"
        )
        cur.execute("INSERT INTO pruebas.cuenta (id, saldo) VALUES (1, 1000.00)")

    bloqueo = psycopg.connect(**parametros_bd)  # type: ignore[arg-type]  # transacción abierta a propósito
    competidor = psycopg.connect(**parametros_bd, autocommit=True)  # type: ignore[arg-type]
    try:
        with bloqueo.cursor() as cur:
            cur.execute("SELECT saldo FROM pruebas.cuenta WHERE id = 1 FOR UPDATE")
            assert cur.fetchone()[0] == Decimal("1000.00")

        with pytest.raises(psycopg.errors.LockNotAvailable), competidor.cursor() as cur:
            cur.execute("SELECT saldo FROM pruebas.cuenta WHERE id = 1 FOR UPDATE NOWAIT")

        bloqueo.rollback()

        with competidor.cursor() as cur:
            cur.execute("SELECT saldo FROM pruebas.cuenta WHERE id = 1 FOR UPDATE NOWAIT")
            assert cur.fetchone()[0] == Decimal("1000.00")
    finally:
        bloqueo.close()
        competidor.close()


def test_transaccion_atomica_revierte_todo(
    conexion: psycopg.Connection, parametros_bd: dict[str, object]
) -> None:
    """Una operación financiera fallida no debe dejar rastro parcial."""
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS pruebas.cuenta_atomica")
        cur.execute(
            "CREATE TABLE pruebas.cuenta_atomica (id int PRIMARY KEY, saldo numeric(18,2) NOT NULL)"
        )
        cur.execute("INSERT INTO pruebas.cuenta_atomica (id, saldo) VALUES (1, 500.00)")

    conn = psycopg.connect(**parametros_bd)  # type: ignore[arg-type]
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE pruebas.cuenta_atomica SET saldo = saldo - 100.00 WHERE id = 1")
            with pytest.raises(psycopg.errors.DivisionByZero):
                cur.execute("SELECT 1 / 0")
        conn.rollback()
    finally:
        conn.close()

    with conexion.cursor() as cur:
        cur.execute("SELECT saldo FROM pruebas.cuenta_atomica WHERE id = 1")
        saldo = cur.fetchone()[0]
    assert saldo == Decimal("500.00"), "La transacción fallida dejó un cambio parcial"


def test_usuario_de_aplicacion_no_es_superusuario(conexion: psycopg.Connection) -> None:
    """Principio de menor privilegio: la aplicación no se conecta como superusuario.

    CREATEDB sí se concede en desarrollo: pytest-django lo necesita para crear la base
    de datos de pruebas. NOCREATEROLE se mantiene siempre.
    """
    with conexion.cursor() as cur:
        cur.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = current_user"
        )
        es_super, puede_crear_bd, puede_crear_roles = cur.fetchone()
    assert es_super is False, "El usuario de la aplicación no debe ser superusuario"
    assert puede_crear_roles is False, "El usuario de la aplicación no debe crear roles"
    assert puede_crear_bd is True, "Debe poder crear la base de datos de pruebas"


def test_puede_crear_objetos_en_su_esquema(conexion: psycopg.Connection) -> None:
    """El usuario debe poder ejecutar migraciones (DDL) en la base del proyecto."""
    with conexion.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS pruebas.migracion")
        cur.execute("CREATE TABLE pruebas.migracion (id serial PRIMARY KEY, dato text)")
        cur.execute("INSERT INTO pruebas.migracion (dato) VALUES ('ok') RETURNING id")
        nuevo_id = cur.fetchone()[0]
        cur.execute("DROP TABLE pruebas.migracion")
    assert nuevo_id == 1
