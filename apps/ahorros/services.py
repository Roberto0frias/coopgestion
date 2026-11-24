from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.auditoria.services import registrar_evento
from apps.usuarios.models import Usuario

from .models import CuentaAhorro, ProductoAhorro

ROLES_LECTURA = tuple(Usuario.Rol.values)
ROLES_CONFIGURACION = (Usuario.Rol.ADMIN, Usuario.Rol.CONTADOR)
ROLES_APERTURA = (Usuario.Rol.ADMIN, Usuario.Rol.OFICIAL)


def _exigir_rol(usuario, roles):
    if not usuario.is_authenticated or not usuario.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no permite realizar esta operación de ahorro.")


@transaction.atomic
def guardar_producto(*, datos, usuario, producto_id=None, request=None):
    _exigir_rol(usuario, ROLES_CONFIGURACION)
    producto = (
        ProductoAhorro.objects.select_for_update().get(pk=producto_id)
        if producto_id
        else ProductoAhorro(creada_por=usuario)
    )
    for campo, valor in datos.items():
        setattr(producto, campo, valor)
    if producto.activa and producto.tasa_anual is None:
        raise ValidationError("La tasa requiere aprobación antes de activar el producto.")
    producto.full_clean()
    producto.save()
    registrar_evento(
        usuario=usuario,
        accion="PRODUCTO_AHORRO_EDITADO" if producto_id else "PRODUCTO_AHORRO_CREADO",
        request=request,
        objeto=producto,
        detalle={"tipo_socio": producto.tipo_socio, "activa": producto.activa},
    )
    return producto


@transaction.atomic
def abrir_cuenta(*, socio_id, producto_id, usuario, request=None):
    _exigir_rol(usuario, ROLES_APERTURA)
    producto = ProductoAhorro.objects.select_for_update().get(pk=producto_id)
    cuenta = CuentaAhorro(
        socio_id=socio_id,
        producto=producto,
        abierta_por=usuario,
        numero=f"P{uuid4().hex[:15]}",
    )
    cuenta.full_clean()
    cuenta.save()
    cuenta.numero = f"AHO-{cuenta.pk:08d}"
    cuenta.save(update_fields=["numero"])
    registrar_evento(
        usuario=usuario,
        accion="CUENTA_AHORRO_ABIERTA",
        request=request,
        objeto=cuenta,
        detalle={"numero": cuenta.numero, "socio_id": cuenta.socio_id, "producto_id": producto.pk},
    )
    return cuenta
