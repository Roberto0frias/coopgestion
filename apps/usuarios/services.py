"""Servicios de usuarios: alta, autenticación con bloqueo y cambio de contraseña.

Toda la lógica de acceso vive aquí para que las vistas permanezcan delgadas y las reglas
se puedan probar sin pasar por HTTP.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from apps.core.exceptions import ErrorDeNegocio, ErrorDeValidacion
from apps.core.models import Sucursal
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import transaction
from django.utils import timezone

from .models import IntentoAcceso, Rol, Usuario

logger = logging.getLogger(__name__)

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos."


def _config(clave: str, por_defecto: int) -> int:
    return int(settings.COOPGESTION.get(clave, por_defecto))


# --------------------------------------------------------------------------- #
# Alta y mantenimiento de usuarios
# --------------------------------------------------------------------------- #
def crear_usuario(
    *,
    username: str,
    email: str,
    nombres: str,
    apellidos: str,
    rol: Rol,
    password: str | None = None,
    sucursal: Sucursal | None = None,
    cedula: str | None = None,
    telefono: str = "",
    debe_cambiar_password: bool = True,
    ejecutado_por: Usuario | None = None,
) -> Usuario:
    """Crea un usuario interno.

    Args:
        username: Nombre de usuario para iniciar sesión (único).
        email: Correo electrónico (único).
        nombres: Nombres de la persona.
        apellidos: Apellidos de la persona.
        rol: Rol que define sus permisos.
        password: Contraseña inicial. Si es ``None``, la cuenta queda inutilizable hasta
            que un administrador la restablezca.
        sucursal: Sucursal asignada.
        cedula: Cédula de 11 dígitos sin guiones.
        telefono: Teléfono de contacto.
        debe_cambiar_password: Exige cambiar la contraseña en el próximo acceso.
        ejecutado_por: Usuario que realiza el alta (queda en la auditoría).

    Returns:
        El usuario creado.

    Raises:
        ErrorDeValidacion: si el rol es de solo lectura con privilegios de gestión, los
            datos son inválidos o la contraseña no cumple la política.
    """
    if password is not None:
        _validar_password(password, usuario=None)

    with transaction.atomic():
        usuario = Usuario.objects.create_user(
            username=username.strip(),
            email=email,
            password=password,
            nombres=nombres.strip(),
            apellidos=apellidos.strip(),
            rol=rol,
            sucursal=sucursal,
            cedula=cedula or None,
            telefono=telefono.strip(),
            debe_cambiar_password=debe_cambiar_password,
            is_active=True,
        )
    logger.info(
        "Usuario creado: %s (rol %s) por %s",
        usuario.username,
        rol.codigo,
        getattr(ejecutado_por, "username", "sistema"),
    )
    return usuario


def actualizar_usuario(
    usuario: Usuario,
    *,
    rol: Rol | None = None,
    sucursal: Sucursal | None = None,
    email: str | None = None,
    nombres: str | None = None,
    apellidos: str | None = None,
    cedula: str | None = None,
    telefono: str | None = None,
    is_active: bool | None = None,
    ejecutado_por: Usuario | None = None,
) -> Usuario:
    """Actualiza los datos de un usuario. Los cambios quedan en la auditoría."""
    if is_active is False and ejecutado_por is not None and usuario.pk == ejecutado_por.pk:
        raise ErrorDeValidacion("No puede desactivar su propio usuario.")

    campos: dict[str, Any] = {}
    if rol is not None:
        campos["rol"] = rol
    if sucursal is not None:
        campos["sucursal"] = sucursal
    if email is not None:
        campos["email"] = email.lower().strip()
    if nombres is not None:
        campos["nombres"] = nombres.strip()
    if apellidos is not None:
        campos["apellidos"] = apellidos.strip()
    if cedula is not None:
        campos["cedula"] = cedula or None
    if telefono is not None:
        campos["telefono"] = telefono.strip()
    if is_active is not None:
        campos["is_active"] = is_active

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        for campo, valor in campos.items():
            setattr(usuario, campo, valor)
        usuario.save(update_fields=[*campos.keys(), "actualizado_en"])
    return usuario


def desbloquear_usuario(usuario: Usuario, *, ejecutado_por: Usuario | None = None) -> Usuario:
    """Quita el bloqueo temporal y reinicia el contador de intentos fallidos."""
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "actualizado_en"])
    logger.info(
        "Bloqueo levantado para %s por %s",
        usuario.username,
        getattr(ejecutado_por, "username", "sistema"),
    )
    return usuario


# --------------------------------------------------------------------------- #
# Contraseñas
# --------------------------------------------------------------------------- #
def _validar_password(password: str, usuario: Usuario | None) -> None:
    """Aplica la política de contraseñas de Django.

    Raises:
        ErrorDeValidacion: si la contraseña no cumple la política.
    """
    try:
        validate_password(password, usuario)
    except ErrorDeDjango as exc:
        raise ErrorDeValidacion(" ".join(exc.messages)) from exc


def cambiar_password(
    usuario: Usuario,
    password_nueva: str,
    *,
    debe_cambiar_password: bool = False,
) -> Usuario:
    """Cambia la contraseña de un usuario.

    Raises:
        ErrorDeValidacion: si la contraseña no cumple la política.
    """
    _validar_password(password_nueva, usuario)
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        usuario.set_password(password_nueva)
        usuario.debe_cambiar_password = debe_cambiar_password
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(
            update_fields=[
                "password",
                "debe_cambiar_password",
                "intentos_fallidos",
                "bloqueado_hasta",
                "actualizado_en",
            ]
        )
    logger.info("Contraseña cambiada para %s", usuario.username)
    return usuario


def restablecer_password(
    usuario: Usuario,
    password_temporal: str,
    *,
    ejecutado_por: Usuario | None = None,
) -> Usuario:
    """Restablece la contraseña de otro usuario y exige el cambio en el próximo acceso.

    Raises:
        ErrorDeValidacion: si se intenta restablecer la propia contraseña por esta vía.
    """
    if ejecutado_por is not None and usuario.pk == ejecutado_por.pk:
        raise ErrorDeValidacion(
            "Para cambiar su propia contraseña use la opción «Cambiar contraseña»."
        )
    usuario = cambiar_password(usuario, password_temporal, debe_cambiar_password=True)
    logger.info(
        "Contraseña restablecida para %s por %s",
        usuario.username,
        getattr(ejecutado_por, "username", "sistema"),
    )
    return usuario


# --------------------------------------------------------------------------- #
# Autenticación con bloqueo por intentos fallidos
# --------------------------------------------------------------------------- #
def obtener_ip(request: Any) -> str | None:
    """Extrae la IP del cliente, considerando el proxy inverso."""
    if request is None:
        return None
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar_intento(
    username: str,
    *,
    exitoso: bool,
    motivo: str = "",
    usuario: Usuario | None = None,
    request: Any = None,
) -> IntentoAcceso:
    """Registra un intento de acceso, exitoso o fallido."""
    return IntentoAcceso.objects.create(
        usuario=usuario,
        username_intentado=(username or "")[:50],
        ip=obtener_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:250] if request else ""),
        exitoso=exitoso,
        motivo_fallo=motivo,
    )


def autenticar(username: str, password: str, *, request: Any = None) -> Usuario:
    """Autentica a un usuario aplicando la política de intentos fallidos.

    Args:
        username: Nombre de usuario.
        password: Contraseña en texto plano.
        request: Petición HTTP para registrar IP y navegador.

    Returns:
        El usuario autenticado.

    Raises:
        ErrorDeNegocio: con un mensaje genérico si las credenciales no son válidas, o
            con el detalle del bloqueo si la cuenta está bloqueada.
    """
    username = (username or "").strip()
    usuario = Usuario.objects.filter(username__iexact=username).first()

    if usuario is None:
        registrar_intento(username, exitoso=False, motivo="usuario inexistente", request=request)
        raise ErrorDeNegocio(MENSAJE_CREDENCIALES)

    if usuario.esta_bloqueado:
        registrar_intento(
            username, exitoso=False, motivo="cuenta bloqueada", usuario=usuario, request=request
        )
        restante = int((usuario.bloqueado_hasta - timezone.now()).total_seconds() // 60) + 1
        raise ErrorDeNegocio(
            "La cuenta está bloqueada por intentos fallidos. Vuelva a intentarlo en "
            f"{restante} minuto(s) o pida a un administrador que la desbloquee."
        )

    if not usuario.is_active:
        registrar_intento(
            username, exitoso=False, motivo="usuario inactivo", usuario=usuario, request=request
        )
        raise ErrorDeNegocio("La cuenta está desactivada. Contacte al administrador.")

    if not usuario.check_password(password):
        _registrar_fallo(usuario, request=request)
        raise ErrorDeNegocio(MENSAJE_CREDENCIALES)

    _registrar_exito(usuario, request=request)
    return usuario


def _registrar_fallo(usuario: Usuario, *, request: Any = None) -> None:
    """Suma un intento fallido y bloquea la cuenta al alcanzar el límite."""
    limite = _config("INTENTOS_LOGIN", 5)
    minutos = _config("MINUTOS_BLOQUEO", 15)
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        usuario.intentos_fallidos += 1
        motivo = "contraseña incorrecta"
        if usuario.intentos_fallidos >= limite:
            usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=minutos)
            motivo = f"bloqueada tras {limite} intentos fallidos"
            logger.warning("Cuenta bloqueada por intentos fallidos: %s", usuario.username)
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "actualizado_en"])
    registrar_intento(
        usuario.username, exitoso=False, motivo=motivo, usuario=usuario, request=request
    )


def _registrar_exito(usuario: Usuario, *, request: Any = None) -> None:
    """Reinicia el contador de intentos y actualiza la fecha del último acceso."""
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.ultimo_acceso = timezone.now()
        usuario.save(
            update_fields=[
                "intentos_fallidos",
                "bloqueado_hasta",
                "ultimo_acceso",
                "actualizado_en",
            ]
        )
    registrar_intento(usuario.username, exitoso=True, usuario=usuario, request=request)
