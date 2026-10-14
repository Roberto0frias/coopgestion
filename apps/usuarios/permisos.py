"""Catálogo de roles y matriz de permisos de COOPGESTION.

Esta matriz es la fuente de verdad del control de acceso. El comando
``python manage.py sembrar_roles`` la aplica sobre la base de datos y es idempotente:
se puede volver a ejecutar cada vez que un módulo declare permisos nuevos.

Corresponde a la matriz aprobada en la Fase 0 (``docs/fase-0/04-roles-y-permisos.md``).
En esta fase solo existen los módulos ``usuarios``, ``core`` y ``auditoria``; las
entradas de ahorros, préstamos, caja y contabilidad se añadirán al construir cada módulo.
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------- #
# Códigos de rol
# --------------------------------------------------------------------------- #
ADMIN = "ADMIN"
CONTADOR = "CONTADOR"
OFICIAL = "OFICIAL"
CAJERO = "CAJERO"
AUDITOR = "AUDITOR"
COMITE = "COMITE"

ROLES: dict[str, dict[str, Any]] = {
    ADMIN: {
        "nombre": "Administrador",
        "descripcion": (
            "Configura el sistema, gestiona usuarios y parámetros y autoriza excepciones. "
            "No puede aprobar sus propias operaciones."
        ),
        "es_solo_lectura": False,
        "orden": 1,
    },
    CONTADOR: {
        "nombre": "Contador",
        "descripcion": (
            "Contabilidad, cierres, provisiones, libros y reportes contables y regulatorios."
        ),
        "es_solo_lectura": False,
        "orden": 2,
    },
    OFICIAL: {
        "nombre": "Oficial de Préstamos",
        "descripcion": (
            "Registra y analiza solicitudes de crédito y da seguimiento a la cartera. "
            "No aprueba ni desembolsa."
        ),
        "es_solo_lectura": False,
        "orden": 3,
    },
    CAJERO: {
        "nombre": "Cajero",
        "descripcion": (
            "Operaciones de ventanilla: depósitos, retiros autorizados, cobros de cuotas "
            "y cierre de su turno de caja."
        ),
        "es_solo_lectura": False,
        "orden": 4,
    },
    COMITE: {
        "nombre": "Gerencia / Comité de Crédito",
        "descripcion": (
            "Aprueba solicitudes de préstamo, retiros sobre el umbral, condonaciones y "
            "castigos. No digita operaciones de caja. Decisión P-13."
        ),
        "es_solo_lectura": False,
        "orden": 5,
    },
    AUDITOR: {
        "nombre": "Auditor",
        "descripcion": (
            "Acceso de solo lectura a toda la información, incluida la bitácora de "
            "auditoría y la verificación de su cadena de integridad."
        ),
        "es_solo_lectura": True,
        "orden": 6,
    },
}

#: Roles que pueden dar la segunda firma en operaciones que la exigen (decisión D-07).
ROLES_APROBADORES: frozenset[str] = frozenset({ADMIN, COMITE})

# --------------------------------------------------------------------------- #
# Matriz de permisos
# --------------------------------------------------------------------------- #
#: ``"*"`` concede todos los permisos existentes (solo para el Administrador).
MATRIZ_PERMISOS: dict[str, set[str]] = {
    ADMIN: {"*"},
    CONTADOR: {
        "usuarios.view_usuario",
        "core.view_sucursal",
        "core.view_parametrosistema",
        "auditoria.puede_ver_auditoria",
        "auditoria.view_registroauditoria",
    },
    OFICIAL: {
        "usuarios.view_usuario",
        "core.view_sucursal",
    },
    CAJERO: {
        "usuarios.view_usuario",
        "core.view_sucursal",
    },
    COMITE: {
        "usuarios.view_usuario",
        "usuarios.view_rol",
        "core.view_sucursal",
        "core.view_parametrosistema",
        "auditoria.puede_ver_auditoria",
        "auditoria.view_registroauditoria",
    },
    AUDITOR: {
        "usuarios.view_usuario",
        "usuarios.view_rol",
        "core.view_sucursal",
        "core.view_moneda",
        "core.view_feriado",
        "core.view_parametrosistema",
        "core.view_secuenciadocumental",
        "auditoria.puede_ver_auditoria",
        "auditoria.puede_verificar_cadena",
        "auditoria.view_registroauditoria",
    },
}

#: Permisos que nunca se conceden a un rol de solo lectura, aunque la matriz los liste.
PERMISOS_PROHIBIDOS_SOLO_LECTURA: frozenset[str] = frozenset(
    {
        "usuarios.puede_gestionar_usuarios",
        "usuarios.puede_restablecer_password",
        "core.puede_gestionar_parametros",
    }
)


def codigos_de_permisos(codigo_rol: str) -> set[str]:
    """Devuelve el conjunto de códigos de permiso declarados para un rol.

    Args:
        codigo_rol: Código del rol (``ADMIN``, ``CAJERO``, …).

    Returns:
        Conjunto de códigos en formato ``app_label.codename``. El valor ``{"*"}``
        significa "todos los permisos".
    """
    return set(MATRIZ_PERMISOS.get(codigo_rol, set()))


def es_solo_lectura(codigo_rol: str) -> bool:
    """Indica si el rol es de solo lectura."""
    return bool(ROLES.get(codigo_rol, {}).get("es_solo_lectura", False))


def usuario_puede_aprobar(usuario: Any) -> bool:
    """Indica si el usuario puede otorgar la segunda firma en una operación sensible."""
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return False
    if getattr(usuario, "is_superuser", False):
        return True
    rol = getattr(usuario, "rol", None)
    return bool(rol and rol.codigo in ROLES_APROBADORES)
