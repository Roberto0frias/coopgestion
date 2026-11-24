from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

MODULOS = {
    "ahorros": ("Ahorros", "Cuentas, depósitos, retiros e intereses."),
    "prestamos": ("Préstamos", "Solicitudes, evaluación, cuotas y seguimiento."),
    "contabilidad": ("Contabilidad", "Partida doble, catálogo de cuentas y períodos."),
    "reportes": ("Reportes", "Información operativa, contable y gerencial."),
}


@login_required
def inicio(request):
    return render(request, "core/inicio.html")


@login_required
def modulo_pendiente(request, modulo: str):
    contexto = MODULOS.get(modulo)
    if contexto is None:
        raise Http404
    return render(
        request,
        "core/modulo_pendiente.html",
        {
            "nombre_modulo": contexto[0],
            "descripcion_modulo": contexto[1],
        },
    )
