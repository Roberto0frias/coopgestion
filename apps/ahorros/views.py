from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import Usuario

from .forms import AperturaCuentaForm, ProductoAhorroForm
from .models import CuentaAhorro, ProductoAhorro
from .services import (
    ROLES_APERTURA,
    ROLES_CONFIGURACION,
    ROLES_LECTURA,
    abrir_cuenta,
    guardar_producto,
)


def _exigir_rol(request, roles):
    if not request.user.tiene_rol(*roles):
        raise PermissionDenied("Tu rol no tiene acceso a esta sección.")


@login_required
def lista(request):
    _exigir_rol(request, ROLES_LECTURA)
    return render(
        request,
        "ahorros/lista.html",
        {
            "cuentas": CuentaAhorro.objects.select_related("socio", "producto")[:100],
            "productos": ProductoAhorro.objects.all(),
            "puede_abrir": request.user.tiene_rol(*ROLES_APERTURA),
            "puede_configurar": request.user.tiene_rol(*ROLES_CONFIGURACION),
            "productos_sin_tasa": ProductoAhorro.objects.filter(tasa_anual__isnull=True).count(),
        },
    )


@login_required
def crear_producto(request):
    _exigir_rol(request, ROLES_CONFIGURACION)
    form = ProductoAhorroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            producto = guardar_producto(
                datos=form.cleaned_data, usuario=request.user, request=request
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Producto {producto.nombre} guardado.")
            return redirect("ahorros:lista")
    return render(request, "ahorros/producto_form.html", {"form": form, "titulo": "Nuevo producto"})


@login_required
def editar_producto(request, pk):
    _exigir_rol(request, ROLES_CONFIGURACION)
    producto = get_object_or_404(ProductoAhorro, pk=pk)
    form = ProductoAhorroForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        try:
            producto = guardar_producto(
                datos=form.cleaned_data, usuario=request.user, producto_id=pk, request=request
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Producto {producto.nombre} actualizado.")
            return redirect("ahorros:lista")
    return render(
        request,
        "ahorros/producto_form.html",
        {"form": form, "titulo": f"Editar {producto.nombre}", "producto": producto},
    )


@login_required
def abrir(request):
    _exigir_rol(request, ROLES_APERTURA)
    form = AperturaCuentaForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            cuenta = abrir_cuenta(
                socio_id=form.cleaned_data["socio"].pk,
                producto_id=form.cleaned_data["producto"].pk,
                usuario=request.user,
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Cuenta {cuenta.numero} abierta sin saldo inicial.")
            return redirect("ahorros:lista")
    return render(request, "ahorros/apertura_form.html", {"form": form})


@login_required
def movimientos_pendientes(request):
    _exigir_rol(request, (Usuario.Rol.ADMIN, Usuario.Rol.CAJERO, Usuario.Rol.CONTADOR))
    return render(request, "ahorros/movimientos_pendientes.html")
