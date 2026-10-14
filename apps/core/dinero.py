"""Aritmética monetaria de COOPGESTION.

Este módulo es la **única puerta de redondeo** del sistema. Toda operación con dinero
pasa por aquí y devuelve ``Decimal``.

Reglas no negociables
---------------------
1. Todo monto es ``Decimal``. Se prohíbe construir un ``Decimal`` desde ``float``.
2. El redondeo ocurre una sola vez, al final de cada cálculo, con ``ROUND_HALF_UP``.
3. En los repartos (cuotas, prorrateos) la suma de las partes es **exactamente** igual al
   total: el residuo de centavos se concentra en la última parte.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")
CERO = Decimal("0.00")

#: Equivalencia de frecuencias acordada (decisión D-02): 1 mes = 4 semanas.
FACTOR_MESES: dict[str, Decimal] = {
    "MENSUAL": Decimal("1"),
    "QUINCENAL": Decimal("0.5"),
    "SEMANAL": Decimal("0.25"),
}

FRECUENCIAS_VALIDAS = tuple(FACTOR_MESES)


class ErrorMonetario(ValueError):
    """Se lanza cuando un valor monetario o un reparto es inválido."""


def a_decimal(valor: Decimal | int | str) -> Decimal:
    """Convierte ``valor`` a ``Decimal`` sin pasar por ``float``.

    Args:
        valor: ``Decimal``, ``int`` o ``str``. Se rechaza ``float`` a propósito.

    Returns:
        El valor como ``Decimal``.

    Raises:
        ErrorMonetario: si el valor es ``float``, ``bool`` o no es convertible.
    """
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, bool):
        raise ErrorMonetario("Un booleano no es un monto válido.")
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, str):
        try:
            return Decimal(valor)
        except Exception as exc:
            raise ErrorMonetario(f"Texto no convertible a Decimal: {valor!r}") from exc
    raise ErrorMonetario(
        f"Tipo no permitido para un monto: {type(valor).__name__}. "
        "Use Decimal, int o str; nunca float."
    )


def cuantizar(valor: Decimal | int | str) -> Decimal:
    """Redondea a 2 decimales con ``ROUND_HALF_UP``.

    Args:
        valor: Monto a redondear.

    Returns:
        Monto con exactamente 2 decimales.
    """
    return a_decimal(valor).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def repartir(total: Decimal | int | str, partes: int) -> list[Decimal]:
    """Divide ``total`` en ``partes`` montos cuya suma es exactamente ``total``.

    Las primeras ``partes - 1`` cuotas son idénticas y la última recibe todo el residuo
    de centavos (decisión D-07). La base se calcula con redondeo **hacia abajo**, nunca
    con ``HALF_UP``: si la base se redondeara hacia arriba, con totales pequeños podría
    ocurrir que ``base × (partes - 1) > total`` y la última parte resultara negativa.

    Invariantes garantizadas:

    * ``sum(partes) == total`` exacto al centavo.
    * Ninguna parte es negativa.
    * Todas las partes son iguales salvo la última, que es igual o mayor y difiere de
      la base en menos de ``partes`` centavos.

    Args:
        total: Monto total a repartir (se cuantiza primero). No puede ser negativo.
        partes: Número de partes, entero mayor que cero.

    Returns:
        Lista de ``Decimal`` que suma exactamente el total cuantizado.

    Raises:
        ErrorMonetario: si ``partes`` no es un entero positivo o ``total`` es negativo.
    """
    if not isinstance(partes, int) or isinstance(partes, bool) or partes <= 0:
        raise ErrorMonetario(f"Número de partes inválido: {partes!r}")
    total_q = cuantizar(total)
    if total_q < CERO:
        raise ErrorMonetario(
            f"No se puede repartir un monto negativo ({total_q}). "
            "Para reversos use el valor absoluto y ajuste el signo al contabilizar."
        )
    if partes == 1:
        return [total_q]
    base = (total_q / partes).quantize(CENTIMO, rounding=ROUND_FLOOR)
    partes_iguales = [base] * (partes - 1)
    ultima = cuantizar(total_q - base * (partes - 1))
    return [*partes_iguales, ultima]


def meses_de_plazo(numero_cuotas: int, frecuencia: str) -> Decimal:
    """Convierte un número de cuotas a meses según la frecuencia pactada.

    Decisión D-02: mensual = 1 mes, quincenal = 0.5 mes, semanal = 0.25 mes.
    """
    if frecuencia not in FACTOR_MESES:
        raise ErrorMonetario(
            f"Frecuencia inválida: {frecuencia!r}. Válidas: {', '.join(FRECUENCIAS_VALIDAS)}"
        )
    if numero_cuotas <= 0:
        raise ErrorMonetario("El número de cuotas debe ser mayor que cero.")
    return Decimal(numero_cuotas) * FACTOR_MESES[frecuencia]


def interes_total_flat(
    capital: Decimal | int | str,
    tasa_mensual: Decimal | int | str,
    numero_cuotas: int,
    frecuencia: str,
) -> Decimal:
    """Interés total por el método de interés simple sobre capital inicial (flat).

    Decisión D-01: ``interés = capital × tasa_mensual × número de meses``.
    El plazo se pacta en meses y solo cambia la frecuencia de pago.

    Args:
        capital: Monto desembolsado.
        tasa_mensual: Tasa mensual expresada como fracción (2 % → ``Decimal("0.02")``).
        numero_cuotas: Cantidad de cuotas del contrato.
        frecuencia: ``MENSUAL``, ``QUINCENAL`` o ``SEMANAL``.

    Returns:
        Interés total cuantizado a 2 decimales.
    """
    capital_d = a_decimal(capital)
    tasa_d = a_decimal(tasa_mensual)
    if capital_d <= 0:
        raise ErrorMonetario("El capital debe ser mayor que cero.")
    if tasa_d < 0:
        raise ErrorMonetario("La tasa no puede ser negativa.")
    meses = meses_de_plazo(numero_cuotas, frecuencia)
    return cuantizar(capital_d * tasa_d * meses)


def tabla_flat(
    capital: Decimal | int | str,
    tasa_mensual: Decimal | int | str,
    numero_cuotas: int,
    frecuencia: str,
) -> dict[str, object]:
    """Genera la tabla de amortización por interés simple (flat).

    Garantías que cumple el resultado:

    * ``sum(capitales) == capital`` exacto al centavo.
    * ``sum(intereses) == interes_total`` exacto al centavo.
    * ``sum(cuotas) == capital + interes_total`` exacto al centavo.

    Args:
        capital: Monto desembolsado.
        tasa_mensual: Tasa mensual como fracción.
        numero_cuotas: Cantidad de cuotas.
        frecuencia: ``MENSUAL``, ``QUINCENAL`` o ``SEMANAL``.

    Returns:
        Diccionario con ``capital``, ``interes_total``, ``total``, ``cuotas``
        (lista de diccionarios con ``numero``, ``capital``, ``interes`` y ``total``).
    """
    capital_d = cuantizar(capital)
    interes_total = interes_total_flat(capital_d, tasa_mensual, numero_cuotas, frecuencia)
    total = cuantizar(capital_d + interes_total)

    # Cada componente se reparte por separado y el residuo de centavos queda en la
    # última cuota. Así ninguna cuota puede tener interés negativo, que es lo que
    # ocurría al repartir el total y restar el capital.
    capitales = repartir(capital_d, numero_cuotas)
    intereses = repartir(interes_total, numero_cuotas)

    detalle: list[dict[str, object]] = [
        {
            "numero": indice,
            "capital": capitales[indice - 1],
            "interes": intereses[indice - 1],
            "total": cuantizar(capitales[indice - 1] + intereses[indice - 1]),
        }
        for indice in range(1, numero_cuotas + 1)
    ]

    _verificar_tabla(capital_d, interes_total, total, detalle)
    return {
        "capital": capital_d,
        "interes_total": interes_total,
        "total": total,
        "cuotas": detalle,
    }


def _verificar_tabla(
    capital: Decimal,
    interes_total: Decimal,
    total: Decimal,
    cuotas: Sequence[dict[str, object]],
) -> None:
    """Verifica las invariantes de la tabla. Falla ruidosamente si algo no cuadra."""
    suma_capital = cuantizar(sum((c["capital"] for c in cuotas), CERO))  # type: ignore[misc]
    suma_interes = cuantizar(sum((c["interes"] for c in cuotas), CERO))  # type: ignore[misc]
    suma_total = cuantizar(sum((c["total"] for c in cuotas), CERO))  # type: ignore[misc]
    if suma_capital != capital:
        raise ErrorMonetario(f"Capital descuadrado: {suma_capital} != {capital}")
    if suma_interes != interes_total:
        raise ErrorMonetario(f"Interés descuadrado: {suma_interes} != {interes_total}")
    if suma_total != total:
        raise ErrorMonetario(f"Total descuadrado: {suma_total} != {total}")


def mora_por_periodo(
    cuota_total: Decimal | int | str,
    periodos_atraso: int,
    porcentaje_periodo: Decimal | int | str,
    tope: Decimal | int | str | None = None,
) -> Decimal:
    """Calcula la mora acumulada por períodos de atraso.

    Decisión D-03: 5 % de la cuota total por cada período transcurrido desde el
    vencimiento, tras los días de gracia. La acumulación es lineal.

    Args:
        cuota_total: Valor de la cuota vencida (capital + interés).
        periodos_atraso: Períodos completos transcurridos desde el vencimiento.
        porcentaje_periodo: Porcentaje por período como fracción (5 % → ``Decimal("0.05")``).
        tope: Tope máximo de mora acumulada. ``None`` significa sin tope.

    Returns:
        Mora acumulada cuantizada a 2 decimales.
    """
    cuota_d = cuantizar(cuota_total)
    porcentaje_d = a_decimal(porcentaje_periodo)
    if periodos_atraso < 0:
        raise ErrorMonetario("Los períodos de atraso no pueden ser negativos.")
    if porcentaje_d < 0:
        raise ErrorMonetario("El porcentaje de mora no puede ser negativo.")
    mora = cuantizar(cuota_d * porcentaje_d * periodos_atraso)
    if tope is not None:
        tope_d = cuantizar(tope)
        if tope_d < 0:
            raise ErrorMonetario("El tope de mora no puede ser negativo.")
        mora = min(mora, tope_d)
    return mora


def interes_ahorro_saldo_promedio(
    saldos_diarios: Iterable[Decimal | int | str],
    tasa_anual: Decimal | int | str,
    base_dias: int = 360,
) -> Decimal:
    """Interés de ahorro por saldo promedio diario.

    Decisión D-04: ``interés = Σ(saldo diario) × tasa_anual / base_dias``.

    Args:
        saldos_diarios: Saldo de cada día del período.
        tasa_anual: Tasa nominal anual como fracción (3 % → ``Decimal("0.03")``).
        base_dias: Base comercial de días (360 por defecto).

    Returns:
        Interés del período cuantizado a 2 decimales.
    """
    if base_dias <= 0:
        raise ErrorMonetario("La base de días debe ser mayor que cero.")
    tasa_d = a_decimal(tasa_anual)
    if tasa_d < 0:
        raise ErrorMonetario("La tasa no puede ser negativa.")
    suma = sum((cuantizar(s) for s in saldos_diarios), CERO)
    if suma < 0:
        raise ErrorMonetario("La suma de saldos diarios no puede ser negativa.")
    return cuantizar(suma * tasa_d / Decimal(base_dias))
