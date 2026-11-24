from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

from .models import Usuario


class AccesoCoopBackend(ModelBackend):
    """Autenticación Django que respeta el bloqueo temporal de la cuenta."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        del request
        if username is None:
            username = kwargs.get(Usuario.USERNAME_FIELD)
        if not username or not password:
            return None
        try:
            usuario = Usuario._default_manager.get_by_natural_key(username)
        except Usuario.DoesNotExist:
            # Ejecuta el hash predeterminado para reducir diferencias de tiempo
            # entre cuentas existentes y nombres de usuario desconocidos.
            Usuario().set_password(password)
            return None
        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > timezone.now():
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
