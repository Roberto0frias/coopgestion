from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"
    label = "usuarios"
    verbose_name = "Usuarios y seguridad"

    def ready(self) -> None:
        from . import signals  # noqa: F401, PLC0415
