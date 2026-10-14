"""Pruebas de los validadores compartidos, incluida la cédula dominicana.

El algoritmo del dígito verificador se prueba con cédulas construidas a partir del propio
algoritmo y con casos de dígito incorrecto. La validación con cédulas reales de la
cooperativa queda como punto abierto P-18.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from apps.core.validators import (
    digito_verificador_cedula,
    limpiar_cedula,
    validar_cedula,
    validar_monto_no_negativo,
    validar_monto_positivo,
)
from django.core.exceptions import ValidationError


def _cedula_valida(base: str) -> str:
    """Construye una cédula con dígito verificador correcto a partir de 10 dígitos."""
    return f"{base}{digito_verificador_cedula(base)}"


class TestCedula:
    def test_limpiar_quita_guiones_y_espacios(self) -> None:
        assert limpiar_cedula("001-1234567-8") == "00112345678"
        assert limpiar_cedula(" 001 1234567 8 ") == "00112345678"
        assert limpiar_cedula("") == ""

    def test_el_digito_verificador_esta_entre_cero_y_nueve(self) -> None:
        for base in ("0011234567", "4021234567", "0010000000", "9999999999"):
            assert 0 <= digito_verificador_cedula(base) <= 9

    def test_acepta_una_cedula_con_digito_correcto(self) -> None:
        cedula = _cedula_valida("0011234567")
        assert validar_cedula(cedula) == cedula
        assert validar_cedula(f"{cedula[:3]}-{cedula[3:10]}-{cedula[10]}") == cedula

    def test_rechaza_digito_verificador_incorrecto(self) -> None:
        correcta = _cedula_valida("0011234567")
        incorrecta = f"{correcta[:10]}{(int(correcta[10]) + 1) % 10}"
        with pytest.raises(ValidationError, match="dígito verificador"):
            validar_cedula(incorrecta)

    @pytest.mark.parametrize(
        "invalida", ["", "001123456", "001123456789", "0011234567A", "abcdefghijk"]
    )
    def test_rechaza_formatos_invalidos(self, invalida: str) -> None:
        with pytest.raises(ValidationError):
            validar_cedula(invalida)

    def test_el_algoritmo_rechaza_la_mayoria_de_digitos_al_azar(self) -> None:
        """El dígito verificador debe descartar 9 de cada 10 combinaciones."""
        base = "0011234567"
        validos: list[int] = []
        for digito in range(10):
            try:
                validar_cedula(f"{base}{digito}")
            except ValidationError:
                continue
            validos.append(digito)
        assert len(validos) == 1, f"Se aceptaron {len(validos)} dígitos: {validos}"


class TestMontos:
    def test_monto_positivo_acepta_texto_y_decimal(self) -> None:
        assert validar_monto_positivo("1500.25") == Decimal("1500.25")
        assert validar_monto_positivo(Decimal("0.01")) == Decimal("0.01")

    @pytest.mark.parametrize("invalido", ["0", "0.00", "-1", Decimal("-0.01")])
    def test_monto_positivo_rechaza_cero_y_negativos(self, invalido: object) -> None:
        with pytest.raises(ValidationError, match="mayor que cero"):
            validar_monto_positivo(invalido)  # type: ignore[arg-type]

    def test_monto_no_negativo_acepta_cero(self) -> None:
        assert validar_monto_no_negativo("0.00") == Decimal("0.00")

    def test_monto_no_negativo_rechaza_negativos(self) -> None:
        with pytest.raises(ValidationError, match="no puede ser negativo"):
            validar_monto_no_negativo("-0.01")

    @pytest.mark.parametrize("invalido", ["no-es-numero", "1,50", "--5"])
    def test_texto_no_numerico_es_rechazado(self, invalido: str) -> None:
        with pytest.raises(ValidationError, match="número válido"):
            validar_monto_no_negativo(invalido)
