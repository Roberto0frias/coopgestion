"""Pruebas de la matriz de roles y permisos.

Verifica tanto lo permitido como lo **prohibido**: en un sistema financiero, un permiso
de más es tan grave como uno de menos.
"""

from __future__ import annotations

import pytest
from apps.usuarios.permisos import (
    ADMIN,
    AUDITOR,
    CAJERO,
    COMITE,
    CONTADOR,
    OFICIAL,
    ROLES,
    usuario_puede_aprobar,
)

pytestmark = pytest.mark.django_db


# (rol, permiso, ¿debe tenerlo?)
CASOS: list[tuple[str, str, bool]] = [
    # Administrador: todo
    (ADMIN, "usuarios.puede_gestionar_usuarios", True),
    (ADMIN, "usuarios.puede_restablecer_password", True),
    (ADMIN, "core.puede_gestionar_parametros", True),
    (ADMIN, "auditoria.puede_ver_auditoria", True),
    (ADMIN, "auditoria.puede_verificar_cadena", True),
    (ADMIN, "usuarios.delete_usuario", True),
    # Contador: consulta contable y auditoría, sin administración
    (CONTADOR, "auditoria.puede_ver_auditoria", True),
    (CONTADOR, "core.view_parametrosistema", True),
    (CONTADOR, "core.puede_gestionar_parametros", False),
    (CONTADOR, "usuarios.puede_gestionar_usuarios", False),
    (CONTADOR, "auditoria.puede_verificar_cadena", False),
    # Oficial de préstamos
    (OFICIAL, "usuarios.view_usuario", True),
    (OFICIAL, "core.view_sucursal", True),
    (OFICIAL, "auditoria.puede_ver_auditoria", False),
    (OFICIAL, "usuarios.puede_gestionar_usuarios", False),
    # Cajero
    (CAJERO, "usuarios.view_usuario", True),
    (CAJERO, "core.view_sucursal", True),
    (CAJERO, "usuarios.change_usuario", False),
    (CAJERO, "auditoria.puede_ver_auditoria", False),
    # Comité de crédito (decisión P-13)
    (COMITE, "auditoria.puede_ver_auditoria", True),
    (COMITE, "core.view_parametrosistema", True),
    (COMITE, "usuarios.puede_gestionar_usuarios", False),
    (COMITE, "core.puede_gestionar_parametros", False),
    # Auditor: solo lectura, pero puede verificar la cadena
    (AUDITOR, "usuarios.view_usuario", True),
    (AUDITOR, "usuarios.view_rol", True),
    (AUDITOR, "core.view_parametrosistema", True),
    (AUDITOR, "auditoria.puede_ver_auditoria", True),
    (AUDITOR, "auditoria.puede_verificar_cadena", True),
    (AUDITOR, "usuarios.puede_gestionar_usuarios", False),
    (AUDITOR, "usuarios.puede_restablecer_password", False),
    (AUDITOR, "core.puede_gestionar_parametros", False),
    (AUDITOR, "usuarios.add_usuario", False),
    (AUDITOR, "usuarios.change_usuario", False),
    (AUDITOR, "usuarios.delete_usuario", False),
]


@pytest.mark.parametrize(("codigo_rol", "permiso", "esperado"), CASOS)
def test_matriz_de_permisos(
    roles: dict, fabrica_usuarios, codigo_rol: str, permiso: str, esperado: bool
) -> None:
    usuario = fabrica_usuarios(codigo_rol)
    assert (
        usuario.has_perm(permiso) is esperado
    ), f"El rol {codigo_rol} {'debería' if esperado else 'no debería'} tener {permiso}"


def test_existen_los_seis_roles(roles: dict) -> None:
    assert set(roles) == set(ROLES), "Deben existir exactamente los roles declarados"


def test_rol_comite_creado_por_decision_p13(roles: dict) -> None:
    comite = roles[COMITE]
    assert comite.nombre == "Gerencia / Comité de Crédito"
    assert comite.activo is True
    assert comite.es_solo_lectura is False


def test_auditor_es_solo_lectura(roles: dict, fabrica_usuarios) -> None:
    """Ningún permiso del Auditor puede modificar datos."""
    auditor = roles[AUDITOR]
    assert auditor.es_solo_lectura is True
    permisos_escritura = [
        f"{p.content_type.app_label}.{p.codename}"
        for p in auditor.permisos.all()
        if p.codename.startswith(("add_", "change_", "delete_"))
    ]
    assert permisos_escritura == [], f"El Auditor tiene permisos de escritura: {permisos_escritura}"
    assert fabrica_usuarios(AUDITOR).es_solo_lectura is True


def test_administrador_tiene_todos_los_permisos(roles: dict) -> None:
    from django.contrib.auth.models import Permission

    assert roles[ADMIN].permisos.count() == Permission.objects.count()


@pytest.mark.parametrize(
    ("codigo_rol", "esperado"),
    [
        (ADMIN, True),
        (COMITE, True),
        (CONTADOR, False),
        (OFICIAL, False),
        (CAJERO, False),
        (AUDITOR, False),
    ],
)
def test_quien_puede_aprobar_operaciones(
    roles: dict, fabrica_usuarios, codigo_rol: str, esperado: bool
) -> None:
    assert fabrica_usuarios(codigo_rol).puede_aprobar is esperado


def test_superusuario_puede_aprobar() -> None:
    from apps.usuarios.models import Usuario

    superusuario = Usuario(username="root", email="root@coopgestion.local", is_superuser=True)
    assert usuario_puede_aprobar(superusuario) is True


def test_usuario_sin_rol_no_tiene_permisos(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios(CAJERO)
    usuario.rol = None
    usuario.save(update_fields=["rol"])
    assert usuario.get_all_permissions() == set()
    assert usuario.has_perm("usuarios.view_usuario") is False


def test_usuario_inactivo_no_tiene_permisos(fabrica_usuarios) -> None:
    usuario = fabrica_usuarios(ADMIN)
    assert usuario.has_perm("usuarios.puede_gestionar_usuarios") is True
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    assert usuario.get_all_permissions() == set()
    assert usuario.has_perm("usuarios.puede_gestionar_usuarios") is False


def test_rol_inactivo_no_otorga_permisos(roles: dict, fabrica_usuarios) -> None:
    usuario = fabrica_usuarios(CONTADOR)
    rol = roles[CONTADOR]
    rol.activo = False
    rol.save(update_fields=["activo"])
    assert usuario.get_all_permissions() == set()


def test_no_se_usan_grupos_de_django(fabrica_usuarios) -> None:
    """Los permisos vienen del rol; los grupos de Django quedan fuera del diseño."""
    usuario = fabrica_usuarios(ADMIN)
    assert usuario.get_group_permissions() == set()
