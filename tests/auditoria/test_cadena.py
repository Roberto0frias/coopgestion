"""Pruebas de la cadena de hash de la bitácora de auditoría.

Lo que se verifica aquí es la propiedad central del módulo: si alguien altera una fila de
la tabla, la verificación debe detectarlo y señalar el registro exacto.

Las aserciones son **relativas**: las fixtures de las pruebas también generan registros de
auditoría (al crear la sucursal, los roles y los usuarios), así que nunca se compara contra
un total absoluto.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from apps.auditoria.context import usar_usuario
from apps.auditoria.models import RegistroAuditoria
from apps.auditoria.services import calcular_hash, contenido_para_hash, registrar, verificar_cadena
from apps.core.exceptions import ErrorDeNegocio
from apps.core.models import Sucursal
from django.db import connection

pytestmark = pytest.mark.django_db


def _registrar_varios(cantidad: int, usuario) -> list[RegistroAuditoria]:
    """Registra ``cantidad`` entradas y devuelve solo las creadas por el bloque."""
    with usar_usuario(usuario):
        return [
            registrar(RegistroAuditoria.Accion.SISTEMA, descripcion=f"evento {indice}")
            for indice in range(cantidad)
        ]


def test_la_primera_entrada_de_todas_arranca_la_cadena(usuario_admin) -> None:
    primera = RegistroAuditoria.objects.order_by("id").first()
    assert primera is not None
    assert primera.hash_anterior == ""
    assert len(primera.hash_registro) == 64


def test_cada_registro_encadena_con_el_anterior(usuario_admin) -> None:
    registros = _registrar_varios(3, usuario_admin)

    assert registros[0].hash_anterior != ""
    assert registros[1].hash_anterior == registros[0].hash_registro
    assert registros[2].hash_anterior == registros[1].hash_registro
    assert len({r.hash_registro for r in registros}) == 3


def test_el_hash_es_reproducible_a_partir_del_contenido(usuario_admin) -> None:
    """El hash debe poder recalcularse: es lo que permite detectar manipulaciones."""
    with usar_usuario(usuario_admin):
        registro = registrar(
            RegistroAuditoria.Accion.CREAR,
            app="core",
            modelo="Sucursal",
            objeto_id=7,
            descripcion="Alta",
            anteriores=None,
            nuevos={"codigo": "CEN"},
        )

    esperado = calcular_hash(registro.hash_anterior, contenido_para_hash(registro))
    assert registro.hash_registro == esperado


def test_verificacion_de_cadena_intacta(usuario_admin) -> None:
    _registrar_varios(5, usuario_admin)

    resultado = verificar_cadena()

    assert resultado["integridad"] is True
    assert resultado["revisados"] == RegistroAuditoria.objects.count()
    assert resultado["primer_error_id"] is None


def test_detecta_registro_alterado(usuario_admin) -> None:
    _registrar_varios(4, usuario_admin)

    objetivo = RegistroAuditoria.objects.order_by("id")[1]
    # update() sobre el QuerySet no pasa por save(): simula exactamente lo que haría
    # alguien manipulando la base de datos directamente.
    RegistroAuditoria.objects.filter(pk=objetivo.pk).update(descripcion="texto manipulado")

    resultado = verificar_cadena()

    assert resultado["integridad"] is False
    assert resultado["primer_error_id"] == objetivo.pk
    assert "no coincide con su hash" in resultado["detalle"]


def test_detecta_fila_insertada_con_encadenamiento_falso(usuario_admin) -> None:
    _registrar_varios(3, usuario_admin)

    RegistroAuditoria.objects.create(
        accion=RegistroAuditoria.Accion.SISTEMA,
        descripcion="inyectada a mano",
        hash_anterior="hash-falso",
        hash_registro="0" * 64,
    )

    resultado = verificar_cadena()

    assert resultado["integridad"] is False
    assert "no apunta al hash del registro anterior" in resultado["detalle"]


def test_verificacion_por_limite_revisa_solo_los_ultimos(usuario_admin) -> None:
    _registrar_varios(5, usuario_admin)

    resultado = verificar_cadena(limite=3)

    assert resultado["integridad"] is True
    assert resultado["revisados"] == 3


def test_un_registro_guardado_no_se_puede_modificar(usuario_admin) -> None:
    registro = _registrar_varios(1, usuario_admin)[0]

    registro.descripcion = "modificado"
    with pytest.raises(ErrorDeNegocio, match="inmutables"):
        registro.save()


def test_un_registro_no_se_puede_eliminar(usuario_admin) -> None:
    registro = _registrar_varios(1, usuario_admin)[0]

    with pytest.raises(ErrorDeNegocio, match="no se pueden eliminar"):
        registro.delete()


def test_no_se_guarda_la_contrasena_en_la_bitacora(usuario_admin, fabrica_usuarios) -> None:
    """Ni la contraseña ni su hash pueden aparecer en el historial."""
    fabrica_usuarios("CAJERO", "secreto")

    registros = RegistroAuditoria.objects.filter(modelo="Usuario")
    assert registros.exists()
    for registro in registros:
        assert "password" not in (registro.valores_nuevos or {})
        assert "password" not in (registro.valores_anteriores or {})


@pytest.mark.django_db(transaction=True)
def test_cadena_intacta_con_escrituras_concurrentes(usuario_admin) -> None:
    """El bloqueo de asesoría debe evitar que dos procesos calculen el mismo hash anterior."""
    cantidad = 8
    antes = RegistroAuditoria.objects.count()

    def crear(indice: int) -> None:
        try:
            with usar_usuario(usuario_admin):
                Sucursal.objects.create(codigo=f"SUC{indice:02d}", nombre=f"Sucursal {indice}")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=4) as ejecutor:
        list(ejecutor.map(crear, range(cantidad)))

    assert Sucursal.objects.filter(codigo__startswith="SUC").count() == cantidad
    assert RegistroAuditoria.objects.count() == antes + cantidad
    resultado = verificar_cadena()
    assert resultado["integridad"] is True, resultado["detalle"]
