from datetime import timedelta

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone

from apps.auditoria.services import registrar_evento

from .models import Usuario


@receiver(user_login_failed)
def registrar_intento_fallido(sender, credentials, request, **kwargs) -> None:
    del sender, kwargs
    username = str(credentials.get("username") or "")
    ahora = timezone.now()
    usuario = None
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().filter(username=username).first()
        if usuario and (not usuario.bloqueado_hasta or usuario.bloqueado_hasta <= ahora):
            usuario.intentos_fallidos += 1
            campos = ["intentos_fallidos"]
            if usuario.intentos_fallidos >= settings.INTENTOS_LOGIN_MAXIMOS:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=settings.MINUTOS_BLOQUEO_LOGIN)
                campos.append("bloqueado_hasta")
            usuario.save(update_fields=campos)
    registrar_evento(
        usuario=usuario,
        accion="ACCESO_FALLIDO",
        request=request,
        objeto=usuario,
        detalle={"usuario_intentado": username[:150]},
    )


@receiver(user_logged_in)
def registrar_inicio_sesion(sender, request, user, **kwargs) -> None:
    del sender, kwargs
    user.ultimo_acceso = timezone.now()
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    user.save(update_fields=["ultimo_acceso", "intentos_fallidos", "bloqueado_hasta"])
    registrar_evento(
        usuario=user,
        accion="INICIO_SESION",
        request=request,
        objeto=user,
    )


@receiver(user_logged_out)
def registrar_cierre_sesion(sender, request, user, **kwargs) -> None:
    del sender, kwargs
    if user and user.is_authenticated:
        registrar_evento(
            usuario=user,
            accion="CIERRE_SESION",
            request=request,
            objeto=user,
        )
