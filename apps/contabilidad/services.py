"""Operaciones del libro diario con bloqueo de período y partida doble."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auditoria.services import registrar_evento
from apps.core.dinero import CERO, ErrorMonetario, a_decimal, cuantizar
from apps.usuarios.models import Usuario

from .models import Asiento, CuentaContable, LineaAsiento, PeriodoContable, SolicitudReverso

ROLES_CONTABILIDAD = (Usuario.Rol.ADMIN, Usuario.Rol.CONTADOR)


def _exigir_rol(usuario: Usuario, roles: tuple[str, ...]) -> None:
    if not usuario.is_authenticated or not usuario.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no permite realizar esta operación contable.")


@transaction.atomic
def abrir_periodo(*, anio: int, mes: int, usuario: Usuario, request=None) -> PeriodoContable:
    _exigir_rol(usuario, ROLES_CONTABILIDAD)
    if not 1 <= mes <= 12 or anio < 2000:
        raise ValidationError("El período contable debe indicar un año y mes válidos.")
    periodo, creado = PeriodoContable.objects.get_or_create(anio=anio, mes=mes)
    if not creado:
        if periodo.estado == PeriodoContable.Estado.CERRADO:
            raise ValidationError("Un período cerrado no se puede reabrir.")
        return periodo
    registrar_evento(
        usuario=usuario,
        accion="PERIODO_CONTABLE_ABIERTO",
        request=request,
        objeto=periodo,
        detalle={"anio": anio, "mes": mes},
    )
    return periodo


def _preparar_lineas(lineas: list[dict]) -> list[dict]:
    if len(lineas) < 2:
        raise ValidationError("Un asiento debe tener al menos dos líneas.")
    preparadas = []
    for numero, linea in enumerate(lineas, start=1):
        try:
            debito = cuantizar(a_decimal(linea.get("debito", "0")))
            credito = cuantizar(a_decimal(linea.get("credito", "0")))
        except ErrorMonetario as error:
            raise ValidationError(str(error)) from error
        if (debito > CERO) == (credito > CERO):
            raise ValidationError(f"La línea {numero} debe tener débito o crédito, nunca ambos.")
        cuenta_id = linea.get("cuenta_id")
        if not cuenta_id:
            raise ValidationError(f"Selecciona una cuenta en la línea {numero}.")
        try:
            cuenta_id = int(cuenta_id)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"La cuenta de la línea {numero} no es válida.") from error
        preparadas.append(
            {
                "numero_linea": numero,
                "cuenta_id": cuenta_id,
                "descripcion": str(linea.get("descripcion", ""))[:180],
                "debito": debito,
                "credito": credito,
            }
        )
    return preparadas


@transaction.atomic
def crear_borrador(
    *,
    fecha: date,
    descripcion: str,
    lineas: list[dict],
    usuario: Usuario,
    request=None,
    clave_idempotencia: UUID | str | None = None,
) -> Asiento:
    _exigir_rol(usuario, ROLES_CONTABILIDAD)
    descripcion = descripcion.strip()
    if not descripcion:
        raise ValidationError({"descripcion": "La descripción es obligatoria."})
    try:
        fecha = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    except ValueError as error:
        raise ValidationError({"fecha": "La fecha del asiento no es válida."}) from error
    if not isinstance(fecha, date) or isinstance(fecha, datetime):
        raise ValidationError({"fecha": "La fecha del asiento no es válida."})
    preparadas = _preparar_lineas(lineas)
    try:
        clave = UUID(str(clave_idempotencia)) if clave_idempotencia else uuid4()
    except ValueError as error:
        raise ValidationError("La clave de operación no es válida.") from error

    existente = Asiento.objects.filter(clave_idempotencia=clave).first()
    if existente:
        return existente

    periodo = abrir_periodo(anio=fecha.year, mes=fecha.month, usuario=usuario, request=request)
    periodo = PeriodoContable.objects.select_for_update().get(pk=periodo.pk)
    existente = Asiento.objects.filter(clave_idempotencia=clave).first()
    if existente:
        return existente
    if periodo.estado != PeriodoContable.Estado.ABIERTO:
        raise ValidationError("No se puede registrar en un período contable cerrado.")
    cuentas = {
        cuenta.pk: cuenta
        for cuenta in CuentaContable.objects.select_for_update()
        .filter(pk__in={linea["cuenta_id"] for linea in preparadas})
        .order_by("pk")
    }
    if len(cuentas) != len({linea["cuenta_id"] for linea in preparadas}):
        raise ValidationError("Una de las cuentas contables seleccionadas no existe.")
    for linea in preparadas:
        cuenta = cuentas[linea["cuenta_id"]]
        if not cuenta.activa or not cuenta.permite_movimiento:
            raise ValidationError(f"La cuenta {cuenta.codigo} no acepta movimientos.")
    asiento = Asiento.objects.create(
        fecha=fecha,
        descripcion=descripcion[:255],
        periodo=periodo,
        creado_por=usuario,
        clave_idempotencia=clave,
    )
    LineaAsiento.objects.bulk_create(
        [LineaAsiento(asiento=asiento, **linea) for linea in preparadas]
    )
    registrar_evento(
        usuario=usuario,
        accion="ASIENTO_BORRADOR_CREADO",
        request=request,
        objeto=asiento,
        detalle={"lineas": len(preparadas), "fecha": fecha.isoformat()},
    )
    return asiento


@transaction.atomic
def confirmar_asiento(*, asiento_id: int, usuario: Usuario, request=None) -> Asiento:
    _exigir_rol(usuario, ROLES_CONTABILIDAD)
    asiento = Asiento.objects.select_for_update().get(pk=asiento_id)
    if asiento.estado != Asiento.Estado.BORRADOR:
        raise ValidationError("Solo se puede confirmar un asiento en borrador.")
    if usuario.rol == Usuario.Rol.ADMIN and asiento.creado_por_id == usuario.pk:
        raise PermissionDenied("Un Administrador no puede confirmar su propio asiento.")
    periodo = PeriodoContable.objects.select_for_update().get(pk=asiento.periodo_id)
    if periodo.estado != PeriodoContable.Estado.ABIERTO:
        raise ValidationError("El período contable del asiento está cerrado.")
    lineas = list(asiento.lineas.order_by("numero_linea"))
    if len(lineas) < 2:
        raise ValidationError("Un asiento debe tener al menos dos líneas.")
    cuentas = {
        cuenta.pk: cuenta
        for cuenta in CuentaContable.objects.select_for_update()
        .filter(pk__in={linea.cuenta_id for linea in lineas})
        .order_by("pk")
    }
    if any(
        not cuentas[linea.cuenta_id].activa or not cuentas[linea.cuenta_id].permite_movimiento
        for linea in lineas
    ):
        raise ValidationError(
            "Todas las cuentas del asiento deben estar activas y aceptar movimientos."
        )
    debitos = cuantizar(sum((linea.debito for linea in lineas), CERO))
    creditos = cuantizar(sum((linea.credito for linea in lineas), CERO))
    if debitos <= CERO or debitos != creditos:
        raise ValidationError(
            f"El asiento no cuadra: débitos RD$ {debitos} y créditos RD$ {creditos}."
        )
    periodo.ultimo_numero_asiento += 1
    periodo.save(update_fields=["ultimo_numero_asiento"])
    asiento.numero = f"{periodo.anio}{periodo.mes:02d}-{periodo.ultimo_numero_asiento:05d}"
    asiento.total_debito = debitos
    asiento.total_credito = creditos
    asiento.estado = Asiento.Estado.CONFIRMADO
    asiento.confirmado_por = usuario
    asiento.confirmado_en = timezone.now()
    asiento.save(
        update_fields=[
            "numero",
            "total_debito",
            "total_credito",
            "estado",
            "confirmado_por",
            "confirmado_en",
        ]
    )
    registrar_evento(
        usuario=usuario,
        accion="ASIENTO_CONFIRMADO",
        request=request,
        objeto=asiento,
        detalle={
            "numero": asiento.numero,
            "total_debito": str(debitos),
            "total_credito": str(creditos),
            "creado_por_id": asiento.creado_por_id,
        },
    )
    return asiento


@transaction.atomic
def cerrar_periodo(*, periodo_id: int, usuario: Usuario, request=None) -> PeriodoContable:
    _exigir_rol(usuario, (Usuario.Rol.CONTADOR,))
    periodo = PeriodoContable.objects.select_for_update().get(pk=periodo_id)
    if periodo.estado != PeriodoContable.Estado.ABIERTO:
        raise ValidationError("El período ya está cerrado.")
    if periodo.asientos.filter(estado=Asiento.Estado.BORRADOR).exists():
        raise ValidationError("No se puede cerrar: quedan asientos en borrador.")
    periodo.estado = PeriodoContable.Estado.CERRADO
    periodo.cerrado_en = timezone.now()
    periodo.cerrado_por = usuario
    periodo.save(update_fields=["estado", "cerrado_en", "cerrado_por"])
    registrar_evento(
        usuario=usuario,
        accion="PERIODO_CONTABLE_CERRADO",
        request=request,
        objeto=periodo,
        detalle={"anio": periodo.anio, "mes": periodo.mes},
    )
    return periodo


@transaction.atomic
def solicitar_reverso(
    *, asiento_id: int, motivo: str, usuario: Usuario, request=None
) -> SolicitudReverso:
    _exigir_rol(usuario, ROLES_CONTABILIDAD)
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError({"motivo": "Explica por qué se necesita el reverso."})
    asiento = Asiento.objects.select_for_update().get(pk=asiento_id)
    if asiento.estado != Asiento.Estado.CONFIRMADO:
        raise ValidationError("Solo se puede solicitar el reverso de un asiento confirmado.")
    if Asiento.objects.filter(reversa_de=asiento).exists():
        raise ValidationError("Este asiento ya tiene un reverso confirmado.")
    if SolicitudReverso.objects.filter(
        asiento=asiento, estado=SolicitudReverso.Estado.PENDIENTE
    ).exists():
        raise ValidationError("Ya hay una solicitud de reverso pendiente para este asiento.")
    solicitud = SolicitudReverso.objects.create(
        asiento=asiento,
        motivo=motivo,
        solicitado_por=usuario,
    )
    registrar_evento(
        usuario=usuario,
        accion="REVERSO_CONTABLE_SOLICITADO",
        request=request,
        objeto=asiento,
        detalle={"solicitud_id": solicitud.pk, "motivo": motivo},
    )
    return solicitud


@transaction.atomic
def resolver_solicitud_reverso(
    *,
    solicitud_id: int,
    aprobar: bool,
    usuario: Usuario,
    request=None,
) -> SolicitudReverso:
    _exigir_rol(usuario, (Usuario.Rol.ADMIN,))
    solicitud = SolicitudReverso.objects.select_for_update().get(pk=solicitud_id)
    if solicitud.estado != SolicitudReverso.Estado.PENDIENTE:
        raise ValidationError("Esta solicitud de reverso ya fue resuelta.")
    if aprobar and solicitud.solicitado_por_id == usuario.pk:
        raise PermissionDenied("No puedes aprobar tu propia solicitud de reverso.")
    ahora = timezone.now()
    if aprobar:
        original = Asiento.objects.select_for_update().get(pk=solicitud.asiento_id)
        if original.estado != Asiento.Estado.CONFIRMADO:
            raise ValidationError("El asiento original ya no está en estado confirmado.")
        if Asiento.objects.filter(reversa_de=original).exists():
            raise ValidationError("Este asiento ya tiene un reverso confirmado.")
        fecha = timezone.localdate()
        periodo = abrir_periodo(
            anio=fecha.year,
            mes=fecha.month,
            usuario=usuario,
            request=request,
        )
        periodo = PeriodoContable.objects.select_for_update().get(pk=periodo.pk)
        if periodo.estado != PeriodoContable.Estado.ABIERTO:
            raise ValidationError(
                "El período actual está cerrado; no se puede contabilizar el reverso."
            )
        originales = list(original.lineas.order_by("numero_linea"))
        periodo.ultimo_numero_asiento += 1
        periodo.save(update_fields=["ultimo_numero_asiento"])
        reverso = Asiento.objects.create(
            numero=f"{periodo.anio}{periodo.mes:02d}-{periodo.ultimo_numero_asiento:05d}",
            fecha=fecha,
            descripcion=f"Reverso de {original.numero}: {solicitud.motivo}"[:255],
            periodo=periodo,
            estado=Asiento.Estado.CONFIRMADO,
            creado_por=solicitud.solicitado_por,
            confirmado_por=usuario,
            confirmado_en=ahora,
            total_debito=original.total_credito,
            total_credito=original.total_debito,
            clave_idempotencia=uuid4(),
            reversa_de=original,
        )
        LineaAsiento.objects.bulk_create(
            [
                LineaAsiento(
                    asiento=reverso,
                    numero_linea=linea.numero_linea,
                    cuenta_id=linea.cuenta_id,
                    descripcion=f"Reverso · {linea.descripcion}"[:180],
                    debito=linea.credito,
                    credito=linea.debito,
                )
                for linea in originales
            ]
        )
        solicitud.asiento_reverso = reverso
        solicitud.estado = SolicitudReverso.Estado.APROBADA
        accion = "REVERSO_CONTABLE_APROBADO"
        detalle = {"solicitud_id": solicitud.pk, "asiento_reverso": reverso.numero}
    else:
        solicitud.estado = SolicitudReverso.Estado.RECHAZADA
        accion = "REVERSO_CONTABLE_RECHAZADO"
        detalle = {"solicitud_id": solicitud.pk, "asiento_original": solicitud.asiento.numero}
    solicitud.resuelto_por = usuario
    solicitud.resuelto_en = ahora
    solicitud.save(update_fields=["estado", "resuelto_por", "resuelto_en", "asiento_reverso"])
    registrar_evento(
        usuario=usuario,
        accion=accion,
        request=request,
        objeto=solicitud.asiento,
        detalle=detalle,
    )
    return solicitud
