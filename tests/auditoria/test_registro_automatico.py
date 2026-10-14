"""Pruebas del registro automático de cambios mediante señales.

Las aserciones se hacen siempre sobre los registros del objeto concreto que se modificó,
nunca sobre el total de la tabla: las fixtures también generan registros de auditoría.
"""

from __future__ import annotations

import pytest
from apps.auditoria.context import usar_usuario
from apps.auditoria.models import RegistroAuditoria
from apps.auditoria.services import verificar_cadena
from apps.core.models import ParametroSistema, Sucursal

pytestmark = pytest.mark.django_db


def _registros_de(instancia) -> list[RegistroAuditoria]:
    """Registros de auditoría de un objeto concreto, en orden cronológico."""
    etiqueta = f"{instancia._meta.app_label}.{instancia.__class__.__name__}"
    app_label, modelo = etiqueta.split(".")
    return list(
        RegistroAuditoria.objects.filter(
            app=app_label, modelo=modelo, objeto_id=str(instancia.pk)
        ).order_by("id")
    )


def test_creacion_queda_registrada(usuario_admin) -> None:
    with usar_usuario(usuario_admin):
        sucursal = Sucursal.objects.create(codigo="NOR", nombre="Sucursal Norte")

    registros = _registros_de(sucursal)
    assert len(registros) == 1
    registro = registros[0]
    assert registro.accion == RegistroAuditoria.Accion.CREAR
    assert registro.usuario_texto == "admin"
    assert registro.valores_nuevos["codigo"] == "NOR"
    assert registro.valores_anteriores is None


def test_actualizacion_guarda_valor_anterior_y_nuevo(usuario_admin, sucursal) -> None:
    with usar_usuario(usuario_admin):
        sucursal.nombre = "Sucursal Central Renombrada"
        sucursal.save()

    registros = _registros_de(sucursal)
    actualizacion = [r for r in registros if r.accion == RegistroAuditoria.Accion.ACTUALIZAR]
    assert len(actualizacion) == 1

    registro = actualizacion[0]
    assert registro.valores_anteriores["nombre"] == "Sucursal Central"
    assert registro.valores_nuevos["nombre"] == "Sucursal Central Renombrada"
    cambios = {c["campo"]: (c["antes"], c["despues"]) for c in registro.resumen_cambios}
    assert cambios["nombre"] == ("Sucursal Central", "Sucursal Central Renombrada")


def test_guardar_sin_cambios_no_genera_registro(usuario_admin, sucursal) -> None:
    """El campo actualizado_en se excluye para no llenar la bitácora de ruido."""
    antes = len(_registros_de(sucursal))

    with usar_usuario(usuario_admin):
        sucursal.save()

    assert len(_registros_de(sucursal)) == antes


def test_eliminacion_queda_registrada(usuario_admin) -> None:
    with usar_usuario(usuario_admin):
        temporal = Sucursal.objects.create(codigo="TMP", nombre="Sucursal Temporal")
        identificador = temporal.pk
        app_label, modelo = temporal._meta.app_label, temporal.__class__.__name__
        temporal.delete()

    registro = RegistroAuditoria.objects.filter(
        app=app_label, modelo=modelo, objeto_id=str(identificador)
    ).latest("id")
    assert registro.accion == RegistroAuditoria.Accion.ELIMINAR
    assert registro.valores_anteriores["codigo"] == "TMP"


def test_una_sucursal_con_usuarios_no_se_puede_eliminar(usuario_admin, sucursal) -> None:
    """Las claves foráneas usan PROTECT: nunca se borra historial en cascada."""
    from django.db.models.deletion import ProtectedError

    with pytest.raises(ProtectedError), usar_usuario(usuario_admin):
        sucursal.delete()


def test_parametro_auditado_con_tipo_y_valor(usuario_admin) -> None:
    with usar_usuario(usuario_admin):
        parametro = ParametroSistema.objects.create(
            clave="PRUEBA_AUDITORIA",
            valor="123.45",
            tipo_dato=ParametroSistema.TipoDato.DECIMAL,
        )

    registro = _registros_de(parametro)[0]
    assert registro.valores_nuevos["clave"] == "PRUEBA_AUDITORIA"
    assert registro.valores_nuevos["valor"] == "123.45"


def test_el_usuario_que_hace_el_cambio_queda_registrado(usuario_admin, usuario_cajero) -> None:
    with usar_usuario(usuario_cajero):
        sucursal = Sucursal.objects.create(codigo="EST", nombre="Sucursal Este")

    registro = _registros_de(sucursal)[0]
    assert registro.usuario_texto == "usuario_cajero"
    assert registro.usuario_id == usuario_cajero.pk


def test_los_registros_se_encadenan_al_crear_varios_objetos(usuario_admin) -> None:
    with usar_usuario(usuario_admin):
        for indice in range(4):
            Sucursal.objects.create(codigo=f"Z{indice}", nombre=f"Sucursal {indice}")

    assert verificar_cadena()["integridad"] is True


def test_alta_de_usuario_registra_el_rol_sin_datos_sensibles(
    usuario_admin, fabrica_usuarios
) -> None:
    with usar_usuario(usuario_admin):
        usuario = fabrica_usuarios("CAJERO", "auditado")

    registro = _registros_de(usuario)[0]
    assert registro.accion == RegistroAuditoria.Accion.CREAR
    assert registro.valores_nuevos["username"] == "auditado"
    assert "password" not in registro.valores_nuevos
    assert registro.valores_nuevos["rol"] == usuario.rol_id


def test_cambio_de_rol_queda_con_valor_anterior(usuario_admin, fabrica_usuarios, roles) -> None:
    usuario = fabrica_usuarios("CAJERO", "promovido")

    with usar_usuario(usuario_admin):
        usuario.rol = roles["COMITE"]
        usuario.save(update_fields=["rol"])

    actualizacion = next(
        r for r in _registros_de(usuario) if r.accion == RegistroAuditoria.Accion.ACTUALIZAR
    )
    assert actualizacion.valores_anteriores["rol"] == roles["CAJERO"].pk
    assert actualizacion.valores_nuevos["rol"] == roles["COMITE"].pk
