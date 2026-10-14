"""Modelos que se auditan automáticamente.

Al construir cada módulo nuevo basta con añadir su modelo aquí para que todos sus cambios
queden registrados con valor anterior y nuevo.
"""

from __future__ import annotations

MODELOS_AUDITADOS: tuple[str, ...] = (
    "usuarios.Usuario",
    "usuarios.Rol",
    "core.Sucursal",
    "core.Moneda",
    "core.Feriado",
    "core.ParametroSistema",
    "core.SecuenciaDocumental",
)

#: Etiquetas legibles para los reportes de auditoría.
NOMBRES_LEGIBLES: dict[str, str] = {
    "usuarios.Usuario": "Usuario",
    "usuarios.Rol": "Rol",
    "core.Sucursal": "Sucursal",
    "core.Moneda": "Moneda",
    "core.Feriado": "Feriado",
    "core.ParametroSistema": "Parámetro del sistema",
    "core.SecuenciaDocumental": "Secuencia documental",
}
