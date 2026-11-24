from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.usuarios.models import Usuario

from .forms import AsientoBorradorForm, LineaAsientoFormSet
from .models import Asiento, PeriodoContable, SolicitudReverso
from .services import (
    ROLES_CONTABILIDAD,
    abrir_periodo,
    confirmar_asiento,
    crear_borrador,
    resolver_solicitud_reverso,
    solicitar_reverso,
)
from .services import (
    cerrar_periodo as cerrar_periodo_servicio,
)

ROLES_LECTURA = tuple(Usuario.Rol.values)


def _exigir_rol(request, roles: tuple[str, ...]) -> None:
    if not request.user.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no tiene acceso a esta sección.")


@login_required
def lista(request):
    _exigir_rol(request, ROLES_LECTURA)
    asientos = Asiento.objects.select_related("periodo", "creado_por", "confirmado_por")
    estado = request.GET.get("estado", "")
    if estado in Asiento.Estado.values:
        asientos = asientos.filter(estado=estado)
    periodos = PeriodoContable.objects.all()[:12]
    hoy = timezone.localdate()
    periodo_actual_abierto = PeriodoContable.objects.filter(
        anio=hoy.year, mes=hoy.month, estado=PeriodoContable.Estado.ABIERTO
    ).exists()
    puede_crear = request.user.tiene_rol(*ROLES_CONTABILIDAD)
    return render(
        request,
        "contabilidad/lista.html",
        {
            "asientos": asientos[:100],
            "estado_seleccionado": estado,
            "estados": Asiento.Estado.choices,
            "periodos": periodos,
            "puede_crear": puede_crear,
            "puede_cerrar_periodo": request.user.tiene_rol(Usuario.Rol.CONTADOR),
            "periodo_actual_abierto": periodo_actual_abierto,
        },
    )


@login_required
def crear(request):
    _exigir_rol(request, ROLES_CONTABILIDAD)
    form = AsientoBorradorForm(request.POST or None, initial={"fecha": timezone.localdate()})
    formset = LineaAsientoFormSet(request.POST or None, prefix="lineas")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        lineas = [
            {
                "cuenta_id": registro["cuenta"].pk,
                "descripcion": registro.get("descripcion", ""),
                "debito": registro.get("debito") or "0",
                "credito": registro.get("credito") or "0",
            }
            for subform in formset.forms
            if (registro := subform.cleaned_data) and registro.get("cuenta")
        ]
        try:
            asiento = crear_borrador(
                fecha=form.cleaned_data["fecha"],
                descripcion=form.cleaned_data["descripcion"],
                lineas=lineas,
                usuario=request.user,
                request=request,
                clave_idempotencia=request.POST.get("clave_idempotencia"),
            )
        except (ValidationError, ValueError) as error:
            if isinstance(error, ValidationError):
                form.add_error(None, error)
            else:
                form.add_error(None, "Revisa las cuentas y montos ingresados.")
        else:
            messages.success(request, "El asiento quedó guardado como borrador.")
            return redirect("contabilidad:detalle", pk=asiento.pk)
    return render(
        request,
        "contabilidad/formulario.html",
        {
            "form": form,
            "formset": formset,
            "clave_idempotencia": uuid4(),
        },
    )


@login_required
def detalle(request, pk: int):
    _exigir_rol(request, ROLES_LECTURA)
    asiento = get_object_or_404(
        Asiento.objects.select_related("periodo", "creado_por", "confirmado_por").prefetch_related(
            "lineas__cuenta"
        ),
        pk=pk,
    )
    puede_confirmar = (
        asiento.estado == Asiento.Estado.BORRADOR
        and request.user.tiene_rol(*ROLES_CONTABILIDAD)
        and not (request.user.rol == Usuario.Rol.ADMIN and asiento.creado_por_id == request.user.pk)
    )
    solicitud_reverso = (
        asiento.solicitudes_reverso.filter(estado=SolicitudReverso.Estado.PENDIENTE)
        .select_related("solicitado_por")
        .first()
    )
    tiene_reverso = Asiento.objects.filter(reversa_de=asiento).first()
    historial_reversos = asiento.solicitudes_reverso.select_related(
        "solicitado_por", "resuelto_por"
    ).order_by("-solicitado_en")
    return render(
        request,
        "contabilidad/detalle.html",
        {
            "asiento": asiento,
            "puede_confirmar": puede_confirmar,
            "puede_solicitar_reverso": (
                asiento.estado == Asiento.Estado.CONFIRMADO
                and request.user.tiene_rol(*ROLES_CONTABILIDAD)
                and not solicitud_reverso
                and not tiene_reverso
            ),
            "solicitud_reverso": solicitud_reverso,
            "puede_resolver_reverso": bool(solicitud_reverso)
            and request.user.tiene_rol(Usuario.Rol.ADMIN)
            and solicitud_reverso.solicitado_por_id != request.user.pk,
            "asiento_reverso": tiene_reverso,
            "historial_reversos": historial_reversos,
            "asiento_original": asiento.reversa_de,
        },
    )


@login_required
def confirmar(request, pk: int):
    if request.method != "POST":
        raise PermissionDenied("La confirmación contable solo acepta POST.")
    try:
        asiento = confirmar_asiento(asiento_id=pk, usuario=request.user, request=request)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, f"El asiento {asiento.numero} fue confirmado.")
    return redirect("contabilidad:detalle", pk=pk)


@login_required
def abrir_periodo_actual(request):
    if request.method != "POST":
        raise PermissionDenied("La apertura del período contable solo acepta POST.")
    hoy = timezone.localdate()
    try:
        abrir_periodo(anio=hoy.year, mes=hoy.month, usuario=request.user, request=request)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, f"Período {hoy.year}-{hoy.month:02d} abierto.")
    return redirect("contabilidad:lista")


@login_required
def cerrar_periodo(request, periodo_id: int):
    if request.method != "POST":
        raise PermissionDenied("El cierre del período contable solo acepta POST.")
    try:
        periodo = cerrar_periodo_servicio(
            periodo_id=periodo_id,
            usuario=request.user,
            request=request,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, f"Período {periodo} cerrado.")
    return redirect("contabilidad:lista")


@login_required
def solicitar_reverso_view(request, pk: int):
    if request.method != "POST":
        raise PermissionDenied("La solicitud de reverso solo acepta POST.")
    motivo = request.POST.get("motivo", "")
    try:
        solicitar_reverso(
            asiento_id=pk,
            motivo=motivo,
            usuario=request.user,
            request=request,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "La solicitud de reverso se envió para aprobación.")
    return redirect("contabilidad:detalle", pk=pk)


@login_required
def resolver_reverso_view(request, solicitud_id: int):
    if request.method != "POST":
        raise PermissionDenied("La resolución de reverso solo acepta POST.")
    solicitud = get_object_or_404(SolicitudReverso, pk=solicitud_id)
    accion = request.POST.get("accion")
    if accion not in ("aprobar", "rechazar"):
        raise PermissionDenied("Acción de reverso no reconocida.")
    aprobar = accion == "aprobar"
    try:
        solicitud = resolver_solicitud_reverso(
            solicitud_id=solicitud_id,
            aprobar=aprobar,
            usuario=request.user,
            request=request,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        solicitud = get_object_or_404(SolicitudReverso, pk=solicitud_id)
    return redirect("contabilidad:detalle", pk=solicitud.asiento_id)
