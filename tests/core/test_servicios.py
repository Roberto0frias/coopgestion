"""Pruebas de los servicios del núcleo: parámetros, secuencias e idempotencia."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from apps.core.exceptions import ErrorDeConcurrencia, ErrorDeConfiguracion, ErrorDeValidacion
from apps.core.models import OperacionIdempotente, ParametroSistema, SecuenciaDocumental
from apps.core.services import (
    asegurar_secuencia,
    ejecutar_una_vez,
    fijar_parametro,
    obtener_parametro,
    siguiente_numero,
    ya_ejecutada,
)
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------- #
# Parámetros del sistema
# --------------------------------------------------------------------------- #
class TestParametros:
    def test_entero_ida_y_vuelta(self) -> None:
        fijar_parametro("PRUEBA_ENTERO", 7, tipo_dato=ParametroSistema.TipoDato.ENTERO)
        assert obtener_parametro("PRUEBA_ENTERO") == 7

    def test_decimal_ida_y_vuelta(self) -> None:
        fijar_parametro("PRUEBA_DECIMAL", "1234.5", tipo_dato=ParametroSistema.TipoDato.DECIMAL)
        valor = obtener_parametro("PRUEBA_DECIMAL")
        assert valor == Decimal("1234.50")
        assert isinstance(valor, Decimal)

    def test_booleano_acepta_varias_formas(self) -> None:
        for escrito in ("true", "1", "sí", "SI", True):
            fijar_parametro("PRUEBA_BOOL", escrito, tipo_dato=ParametroSistema.TipoDato.BOOLEANO)
            assert obtener_parametro("PRUEBA_BOOL") is True

        fijar_parametro("PRUEBA_BOOL", "false", tipo_dato=ParametroSistema.TipoDato.BOOLEANO)
        assert obtener_parametro("PRUEBA_BOOL") is False

    def test_json_ida_y_vuelta(self) -> None:
        fijar_parametro(
            "PRUEBA_JSON",
            {"tramos": [1, 2, 3]},
            tipo_dato=ParametroSistema.TipoDato.JSON,
        )
        assert obtener_parametro("PRUEBA_JSON") == {"tramos": [1, 2, 3]}

    def test_parametro_inexistente_devuelve_el_valor_por_defecto(self) -> None:
        assert obtener_parametro("NO_EXISTE") is None
        assert obtener_parametro("NO_EXISTE", "respaldo") == "respaldo"

    def test_valor_incompatible_con_el_tipo_es_rechazado(self) -> None:
        with pytest.raises(ErrorDeValidacion):
            fijar_parametro(
                "PRUEBA_MALA", "no-es-numero", tipo_dato=ParametroSistema.TipoDato.ENTERO
            )

    def test_actualizar_conserva_el_tipo(self) -> None:
        fijar_parametro("PRUEBA_ACT", 1, tipo_dato=ParametroSistema.TipoDato.ENTERO)
        fijar_parametro("PRUEBA_ACT", 2)
        parametro = ParametroSistema.objects.get(clave="PRUEBA_ACT")
        assert parametro.tipo_dato == ParametroSistema.TipoDato.ENTERO
        assert obtener_parametro("PRUEBA_ACT") == 2

    def test_la_tasa_de_ahorro_no_esta_sembrada(self) -> None:
        """Decisión P-04: la tasa queda vacía hasta que la administración la defina.

        Mientras no exista, el cálculo de intereses debe fallar con un mensaje claro en
        lugar de inventar una tasa.
        """
        assert obtener_parametro("TASA_INTERES_AHORRO") is None

    def test_umbral_de_doble_firma_sembrado(self) -> None:
        from io import StringIO

        from django.core.management import call_command

        call_command("sembrar_datos_iniciales", stdout=StringIO())
        assert obtener_parametro("UMBRAL_RETIRO_DOBLE_FIRMA") == Decimal("50000.00")


# --------------------------------------------------------------------------- #
# Secuencias documentales
# --------------------------------------------------------------------------- #
class TestSecuencias:
    def test_numero_con_prefijo_y_longitud(self) -> None:
        asegurar_secuencia("RECIBO_PAGO", prefijo="REC-", longitud=6)
        assert siguiente_numero("RECIBO_PAGO") == "REC-000001"
        assert siguiente_numero("RECIBO_PAGO") == "REC-000002"

    def test_secuencia_inexistente_falla_con_mensaje_claro(self) -> None:
        with pytest.raises(ErrorDeConfiguracion, match="secuencia activa"):
            siguiente_numero("NO_EXISTE")

    def test_secuencia_inactiva_no_se_usa(self) -> None:
        secuencia = asegurar_secuencia("ANULADA", prefijo="A-")
        secuencia.activa = False
        secuencia.save(update_fields=["activa"])
        with pytest.raises(ErrorDeConfiguracion):
            siguiente_numero("ANULADA")

    def test_no_puede_haber_dos_secuencias_globales_del_mismo_tipo(self) -> None:
        asegurar_secuencia("DUPLICADA")
        with pytest.raises(IntegrityError):
            SecuenciaDocumental.objects.create(tipo="DUPLICADA")

    def test_secuencias_por_sucursal_son_independientes(self, sucursal) -> None:
        global_ = asegurar_secuencia("MIXTA", prefijo="G-")
        por_sucursal = asegurar_secuencia("MIXTA", prefijo="S-", sucursal=sucursal)
        assert global_.pk != por_sucursal.pk

        assert siguiente_numero("MIXTA") == "G-000001"
        assert siguiente_numero("MIXTA", sucursal=sucursal) == "S-000001"
        assert siguiente_numero("MIXTA") == "G-000002"

    @pytest.mark.django_db(transaction=True)
    def test_los_numeros_no_se_repiten_bajo_concurrencia(self) -> None:
        """Dos cajeros concurrentes no pueden recibir el mismo número.

        Se usa ``transaction=True`` porque cada hilo abre su propia conexión y necesita
        ver la secuencia ya confirmada.
        """
        from concurrent.futures import ThreadPoolExecutor

        from django.db import connection

        asegurar_secuencia("CONCURRENTE", prefijo="C-", longitud=6)

        def reservar(_: int) -> str:
            try:
                return siguiente_numero("CONCURRENTE")
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            numeros = list(ejecutor.map(reservar, range(8)))

        assert len(set(numeros)) == 8, f"Se repitieron números: {numeros}"
        assert sorted(numeros) == [f"C-{indice:06d}" for indice in range(1, 9)]


# --------------------------------------------------------------------------- #
# Idempotencia
# --------------------------------------------------------------------------- #
class TestIdempotencia:
    def test_la_operacion_se_ejecuta_una_sola_vez(self) -> None:
        clave = uuid.uuid4()
        ejecuciones = []

        def operacion() -> int:
            ejecuciones.append(1)
            return 42

        assert ejecutar_una_vez(clave, "ahorros", "deposito", operacion) == 42
        assert len(ejecuciones) == 1
        assert ya_ejecutada(clave) is True

    def test_reintento_con_la_misma_clave_es_rechazado(self) -> None:
        clave = uuid.uuid4()
        ejecutar_una_vez(clave, "ahorros", "deposito", lambda: 1)

        with pytest.raises(ErrorDeConcurrencia, match="ya fue registrada"):
            ejecutar_una_vez(clave, "ahorros", "deposito", lambda: 2)

        assert OperacionIdempotente.objects.filter(clave=clave).count() == 1

    def test_claves_distintas_ejecutan_ambas(self) -> None:
        primera, segunda = uuid.uuid4(), uuid.uuid4()
        assert ejecutar_una_vez(primera, "ahorros", "deposito", lambda: 1) == 1
        assert ejecutar_una_vez(segunda, "ahorros", "deposito", lambda: 2) == 2

    def test_acepta_la_clave_como_texto(self) -> None:
        clave = str(uuid.uuid4())
        assert ejecutar_una_vez(clave, "caja", "cierre", lambda: 5) == 5
        assert ya_ejecutada(clave) is True
