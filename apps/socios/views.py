from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import Usuario

from .forms import RechazoAdmisionForm, SocioForm
from .models import Socio
from .services import (
    ROLES_ADMISION,
    ROLES_EDICION,
    ROLES_LECTURA,
    aprobar_admision,
    editar_socio,
    rechazar_admision,
    registrar_socio,
)


def _exigir_rol(request, roles: tuple[str, ...]) -> None:
    if not request.user.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no tiene acceso a esta sección.")


@login_required
def lista(request):
    _exigir_rol(request, ROLES_LECTURA)
    socios = Socio.objects.all()
    consulta = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    if consulta:
        filtros = (
            Q(codigo__icontains=consulta)
            | Q(nombres__icontains=consulta)
            | Q(apellidos__icontains=consulta)
        )
        if request.user.tiene_rol(Usuario.Rol.ADMIN, Usuario.Rol.OFICIAL):
            filtros |= Q(cedula__icontains=consulta)
        socios = socios.filter(filtros)
    if estado in Socio.Estado.values:
        socios = socios.filter(estado=estado)
    mostrar_cedula = request.user.tiene_rol(Usuario.Rol.ADMIN, Usuario.Rol.OFICIAL)
    return render(
        request,
        "socios/lista.html",
        {
            "socios": socios,
            "consulta": consulta,
            "estado_seleccionado": estado,
            "estados": Socio.Estado.choices,
            "puede_crear": request.user.tiene_rol(*ROLES_EDICION),
            "mostrar_cedula": mostrar_cedula,
        },
    )


@login_required
def crear(request):
    _exigir_rol(request, ROLES_EDICION)
    form = SocioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            socio = registrar_socio(
                datos=form.cleaned_data,
                usuario=request.user,
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Expediente {socio.codigo} registrado para admisión.")
            return redirect("socios:detalle", pk=socio.pk)
    return render(request, "socios/formulario.html", {"form": form, "titulo": "Registrar socio"})


@login_required
def detalle(request, pk: int):
    _exigir_rol(request, ROLES_LECTURA)
    socio = get_object_or_404(Socio, pk=pk)
    return render(
        request,
        "socios/detalle.html",
        {
            "socio": socio,
            "puede_editar": request.user.tiene_rol(*ROLES_EDICION)
            and socio.estado not in (Socio.Estado.RECHAZADO, Socio.Estado.RETIRADO),
            "puede_resolver": request.user.tiene_rol(*ROLES_ADMISION)
            and socio.estado == Socio.Estado.PENDIENTE
            and socio.creado_por_id != request.user.pk,
            "puede_ver_cedula": request.user.tiene_rol(Usuario.Rol.ADMIN, Usuario.Rol.OFICIAL),
            "rechazo_form": RechazoAdmisionForm(),
        },
    )


@login_required
def editar(request, pk: int):
    _exigir_rol(request, ROLES_EDICION)
    socio = get_object_or_404(Socio, pk=pk)
    if socio.estado in (Socio.Estado.RECHAZADO, Socio.Estado.RETIRADO):
        raise PermissionDenied("No se puede editar un expediente cerrado.")
    form = SocioForm(request.POST or None, instance=socio)
    if request.method == "POST" and form.is_valid():
        try:
            socio = editar_socio(
                socio_id=socio.pk,
                datos=form.cleaned_data,
                usuario=request.user,
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Los datos del socio fueron actualizados.")
            return redirect("socios:detalle", pk=socio.pk)
    return render(
        request,
        "socios/formulario.html",
        {"form": form, "titulo": f"Editar {socio.codigo}", "socio": socio},
    )


@login_required
def resolver_admision(request, pk: int):
    if request.method != "POST":
        raise PermissionDenied("La admisión solo se resuelve mediante POST.")
    socio = get_object_or_404(Socio, pk=pk)
    accion = request.POST.get("accion")
    try:
        if accion == "aprobar":
            aprobar_admision(socio_id=pk, usuario=request.user, request=request)
            messages.success(request, f"El socio {socio.codigo} fue admitido.")
        elif accion == "rechazar":
            form = RechazoAdmisionForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Escribe el motivo para rechazar la admisión.")
                return redirect("socios:detalle", pk=pk)
            rechazar_admision(
                socio_id=pk,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
                request=request,
            )
            messages.warning(request, f"Se rechazó la admisión de {socio.codigo}.")
        else:
            raise PermissionDenied("Acción de admisión no reconocida.")
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("socios:detalle", pk=pk)
