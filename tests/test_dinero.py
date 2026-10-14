"""Pruebas de la aritmética monetaria: la base de la integridad financiera.

Todos los valores esperados están calculados a mano según las decisiones D-01 a D-04
registradas en docs/fase-0/00-levantamiento-y-decisiones.md.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from apps.core import dinero
from apps.core.dinero import (
    CERO,
    FACTOR_MESES,
    ErrorMonetario,
    a_decimal,
    cuantizar,
    interes_ahorro_saldo_promedio,
    interes_total_flat,
    meses_de_plazo,
    mora_por_periodo,
    repartir,
    tabla_flat,
)
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.calculos


class TestCuantizar:
    def test_redondeo_half_up_hacia_arriba(self) -> None:
        assert cuantizar(Decimal("2.345")) == Decimal("2.35")
        assert cuantizar(Decimal("0.005")) == Decimal("0.01")

    def test_redondeo_half_up_hacia_abajo(self) -> None:
        assert cuantizar(Decimal("2.344")) == Decimal("2.34")
        assert cuantizar(Decimal("0.004")) == Decimal("0.00")

    def test_siempre_dos_decimales(self) -> None:
        resultado = cuantizar(Decimal("1000"))
        assert resultado == Decimal("1000.00")
        assert str(resultado) == "1000.00"

    def test_acepta_texto_y_entero(self) -> None:
        assert cuantizar("123.456") == Decimal("123.46")
        assert cuantizar(5) == Decimal("5.00")

    def test_rechaza_float(self) -> None:
        with pytest.raises(ErrorMonetario, match="float"):
            a_decimal(1.5)

    def test_rechaza_booleano(self) -> None:
        with pytest.raises(ErrorMonetario):
            a_decimal(True)

    def test_rechaza_texto_invalido(self) -> None:
        with pytest.raises(ErrorMonetario):
            a_decimal("no es un número")


class TestRepartir:
    def test_suma_exacta_con_residuo(self) -> None:
        partes = repartir(Decimal("100.00"), 3)
        assert partes == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        assert sum(partes) == Decimal("100.00")

    def test_suma_exacta_un_centimo(self) -> None:
        partes = repartir(Decimal("0.01"), 12)
        assert sum(partes) == Decimal("0.01")

    def test_una_sola_parte(self) -> None:
        assert repartir(Decimal("50.00"), 1) == [Decimal("50.00")]

    def test_cero(self) -> None:
        assert repartir(CERO, 4) == [CERO, CERO, CERO, CERO]

    @pytest.mark.parametrize("partes", [0, -1, 2.5, True])
    def test_partes_invalidas(self, partes: object) -> None:
        with pytest.raises(ErrorMonetario):
            repartir(Decimal("10.00"), partes)  # type: ignore[arg-type]


class TestMesesDePlazo:
    def test_equivalencia_de_frecuencias(self) -> None:
        assert meses_de_plazo(12, "MENSUAL") == Decimal("12")
        assert meses_de_plazo(12, "QUINCENAL") == Decimal("6")
        assert meses_de_plazo(12, "SEMANAL") == Decimal("3")
        assert meses_de_plazo(1, "SEMANAL") == Decimal("0.25")

    def test_frecuencia_invalida(self) -> None:
        with pytest.raises(ErrorMonetario, match="Frecuencia"):
            meses_de_plazo(12, "DIARIA")


class TestInteresTotalFlat:
    def test_socios_plenos_mensual(self) -> None:
        """10,000.00 al 2 % mensual a 12 meses = 2,400.00 de interés."""
        assert interes_total_flat("10000.00", "0.02", 12, "MENSUAL") == Decimal("2400.00")

    def test_semanal_12_cuotas_equivale_a_3_meses(self) -> None:
        """10,000.00 al 2 % a 12 semanas = 3 meses = 600.00 de interés."""
        assert interes_total_flat("10000.00", "0.02", 12, "SEMANAL") == Decimal("600.00")

    def test_quincenal_12_cuotas_equivale_a_6_meses(self) -> None:
        assert interes_total_flat("10000.00", "0.02", 12, "QUINCENAL") == Decimal("1200.00")

    def test_socios_ahorrantes_3_por_ciento(self) -> None:
        """5,000.00 al 3 % mensual a 6 meses = 900.00."""
        assert interes_total_flat("5000.00", "0.03", 6, "MENSUAL") == Decimal("900.00")

    def test_voluntarias_2_por_ciento(self) -> None:
        assert interes_total_flat("3000.00", "0.02", 10, "SEMANAL") == Decimal("150.00")

    def test_redondeo_del_interes(self) -> None:
        """1,000.01 al 2 % a 7 semanas = 1.75 meses = 35.00035 → 35.00."""
        assert interes_total_flat("1000.01", "0.02", 7, "SEMANAL") == Decimal("35.00")

    def test_capital_invalido(self) -> None:
        with pytest.raises(ErrorMonetario):
            interes_total_flat("0", "0.02", 12, "MENSUAL")

    def test_tasa_negativa(self) -> None:
        with pytest.raises(ErrorMonetario):
            interes_total_flat("1000.00", "-0.01", 12, "MENSUAL")


class TestTablaFlat:
    def test_caso_mensual_calculado_a_mano(self) -> None:
        tabla = tabla_flat("10000.00", "0.02", 12, "MENSUAL")
        assert tabla["interes_total"] == Decimal("2400.00")
        assert tabla["total"] == Decimal("12400.00")
        cuotas = tabla["cuotas"]
        assert len(cuotas) == 12
        # Cuota nivelada esperada: 12400 / 12 = 1033.333... → 1033.33 (última absorbe el residuo)
        assert all(c["total"] == Decimal("1033.33") for c in cuotas[:-1])
        assert cuotas[-1]["total"] == Decimal("1033.37")
        assert all(c["capital"] == Decimal("833.33") for c in cuotas[:-1])
        assert cuotas[-1]["capital"] == Decimal("833.37")
        assert all(c["interes"] == Decimal("200.00") for c in cuotas)

    def test_suma_exacta_de_componentes(self) -> None:
        tabla = tabla_flat("10000.00", "0.02", 12, "MENSUAL")
        assert sum(c["capital"] for c in tabla["cuotas"]) == Decimal("10000.00")
        assert sum(c["interes"] for c in tabla["cuotas"]) == Decimal("2400.00")
        assert sum(c["total"] for c in tabla["cuotas"]) == Decimal("12400.00")

    def test_semanal_calculado_a_mano(self) -> None:
        """5,000.00 al 2 % a 12 semanas: interés 300.00, total 5,300.00."""
        tabla = tabla_flat("5000.00", "0.02", 12, "SEMANAL")
        assert tabla["interes_total"] == Decimal("300.00")
        assert sum(c["total"] for c in tabla["cuotas"]) == Decimal("5300.00")

    def test_una_sola_cuota(self) -> None:
        tabla = tabla_flat("1000.00", "0.02", 1, "MENSUAL")
        assert tabla["cuotas"][0]["total"] == Decimal("1020.00")

    def test_interes_muy_pequeno_no_genera_negativos(self) -> None:
        """Caso límite: interés de 1 centavo repartido en 3 cuotas."""
        tabla = tabla_flat("1.00", "0.0001", 3, "MENSUAL")
        assert all(c["interes"] >= CERO for c in tabla["cuotas"])
        assert sum(c["interes"] for c in tabla["cuotas"]) == tabla["interes_total"]

    def test_cuotas_iguales_salvo_la_ultima(self) -> None:
        """Todas las cuotas son iguales excepto la última, que absorbe el residuo.

        7,777.77 al 3 % a 7 quincenas: interés 816.67 y capital 7,777.77, ambos con
        residuo. La última cuota concentra los dos residuos (decisión D-07).
        """
        tabla = tabla_flat("7777.77", "0.03", 7, "QUINCENAL")
        cuotas = tabla["cuotas"]
        montos = [c["total"] for c in cuotas]
        assert len(set(montos[:-1])) == 1, "Todas las cuotas salvo la última deben ser iguales"
        assert montos[-1] >= montos[0], "La última cuota concentra el residuo, nunca menos"
        # El residuo de cada componente es menor que el número de cuotas (en centavos),
        # por lo que la desviación total acotada es 2 × (cuotas - 1) centavos.
        assert montos[-1] - montos[0] <= Decimal("0.12")


class TestMora:
    def test_tres_periodos_de_atraso(self) -> None:
        """Cuota de 1,000.00 con 3 períodos de atraso al 5 % = 150.00."""
        assert mora_por_periodo("1000.00", 3, "0.05") == Decimal("150.00")

    def test_un_periodo(self) -> None:
        assert mora_por_periodo("1033.33", 1, "0.05") == Decimal("51.67")

    def test_dentro_de_la_gracia(self) -> None:
        assert mora_por_periodo("1000.00", 0, "0.05") == CERO

    def test_tope_maximo(self) -> None:
        """Sin tope serían 300.00; con tope de 100.00 se cobra 100.00."""
        assert mora_por_periodo("1000.00", 6, "0.05") == Decimal("300.00")
        assert mora_por_periodo("1000.00", 6, "0.05", tope="100.00") == Decimal("100.00")

    def test_parametros_invalidos(self) -> None:
        with pytest.raises(ErrorMonetario):
            mora_por_periodo("1000.00", -1, "0.05")
        with pytest.raises(ErrorMonetario):
            mora_por_periodo("1000.00", 2, "-0.05")


class TestInteresAhorro:
    def test_saldo_constante_30_dias(self) -> None:
        """100,000.00 durante 30 días al 3 % anual, base 360 = 250.00."""
        saldos = [Decimal("100000.00")] * 30
        assert interes_ahorro_saldo_promedio(saldos, "0.03") == Decimal("250.00")

    def test_saldos_variables(self) -> None:
        # 10 días a 10,000 y 20 días a 20,000 = 100,000 + 400,000 = 500,000
        # 500,000 × 0.03 / 360 = 41.666... → 41.67
        saldos = [Decimal("10000.00")] * 10 + [Decimal("20000.00")] * 20
        assert interes_ahorro_saldo_promedio(saldos, "0.03") == Decimal("41.67")

    def test_sin_movimiento_no_genera_interes(self) -> None:
        assert interes_ahorro_saldo_promedio([CERO] * 30, "0.03") == CERO

    def test_base_dias_invalida(self) -> None:
        with pytest.raises(ErrorMonetario):
            interes_ahorro_saldo_promedio([Decimal("1.00")], "0.03", base_dias=0)


@given(
    capital=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("5000000.00"), places=2),
    cuotas=st.integers(min_value=1, max_value=120),
    frecuencia=st.sampled_from(sorted(FACTOR_MESES)),
    tasa=st.sampled_from([Decimal("0.02"), Decimal("0.03"), Decimal("0.0001")]),
)
def test_propiedad_la_tabla_siempre_cuadra(
    capital: Decimal, cuotas: int, frecuencia: str, tasa: Decimal
) -> None:
    """Propiedad: en cualquier combinación válida, las sumas son exactas."""
    tabla = tabla_flat(capital, tasa, cuotas, frecuencia)
    detalle = tabla["cuotas"]
    assert sum(c["capital"] for c in detalle) == tabla["capital"]
    assert sum(c["interes"] for c in detalle) == tabla["interes_total"]
    assert sum(c["total"] for c in detalle) == tabla["total"]
    assert all(c["capital"] >= CERO and c["interes"] >= CERO for c in detalle)
    assert tabla["total"] == tabla["capital"] + tabla["interes_total"]
    if cuotas > 1:
        montos = [c["total"] for c in detalle]
        assert len(set(montos[:-1])) == 1, "Solo la última cuota puede diferir"


@given(
    total=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000.00"), places=2),
    partes=st.integers(min_value=1, max_value=360),
)
def test_propiedad_del_reparto(total: Decimal, partes: int) -> None:
    """Propiedad: repartir nunca pierde ni inventa centavos."""
    trozos = repartir(total, partes)
    assert len(trozos) == partes
    assert sum(trozos) == cuantizar(total)


class TestCasosDeError:
    """Rutas de error que protegen contra datos imposibles."""

    def test_repartir_monto_negativo(self) -> None:
        with pytest.raises(ErrorMonetario, match="negativo"):
            repartir("-10.00", 3)

    def test_meses_con_cero_cuotas(self) -> None:
        with pytest.raises(ErrorMonetario, match="mayor que cero"):
            meses_de_plazo(0, "MENSUAL")

    def test_mora_con_tope_negativo(self) -> None:
        with pytest.raises(ErrorMonetario, match="tope"):
            mora_por_periodo("1000.00", 2, "0.05", tope="-1.00")

    def test_ahorro_con_tasa_negativa(self) -> None:
        with pytest.raises(ErrorMonetario, match="tasa"):
            interes_ahorro_saldo_promedio([Decimal("100.00")], "-0.01")

    def test_ahorro_con_saldos_negativos(self) -> None:
        with pytest.raises(ErrorMonetario, match="saldos diarios"):
            interes_ahorro_saldo_promedio([Decimal("-5.00")], "0.03")


class TestGuardianesDeIntegridad:
    """La verificación interna de la tabla debe abortar si algo no cuadra.

    Es la última línea de defensa: si un error de programación produjera una tabla
    inconsistente, el sistema debe fallar ruidosamente en lugar de entregar cifras
    torcidas al socio.
    """

    def test_detecta_capital_descuadrado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dinero, "repartir", lambda _total, partes: [Decimal("1.00")] * partes)
        with pytest.raises(ErrorMonetario, match="Capital descuadrado"):
            dinero.tabla_flat("100.00", "0.02", 3, "MENSUAL")

    def test_detecta_interes_descuadrado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        original = dinero.repartir
        llamadas = {"n": 0}

        def repartir_falso(total: object, partes: int) -> list[Decimal]:
            llamadas["n"] += 1
            if llamadas["n"] == 1:
                return original(total, partes)  # type: ignore[arg-type]  # capitales correctos
            return [CERO] * partes  # intereses en cero: la tabla no cuadra

        monkeypatch.setattr(dinero, "repartir", repartir_falso)
        with pytest.raises(ErrorMonetario, match="Interés descuadrado"):
            dinero.tabla_flat("100.00", "0.02", 3, "MENSUAL")

    def test_detecta_total_descuadrado(self) -> None:
        cuotas: list[dict[str, object]] = [
            {
                "numero": 1,
                "capital": Decimal("10.00"),
                "interes": Decimal("1.00"),
                "total": Decimal("99.00"),
            }
        ]
        with pytest.raises(ErrorMonetario, match="Total descuadrado"):
            dinero._verificar_tabla(Decimal("10.00"), Decimal("1.00"), Decimal("11.00"), cuotas)
