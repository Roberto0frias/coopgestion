"""Configuración de desarrollo local.

Uso: ``DJANGO_SETTINGS_MODULE=config.settings.dev`` (valor por defecto de ``manage.py``).
"""

from __future__ import annotations

from .base import *  # noqa: F403
from .base import BASE_DIR, LOGGING, env

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]  # noqa: S104

# En desarrollo el correo se imprime en la consola.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = ["127.0.0.1"]

# El manejador de archivo necesita que el directorio exista antes de escribir.
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

# Registro más verboso y también en archivo para poder revisar errores.
LOGGING["handlers"]["archivo"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(BASE_DIR / "logs" / "desarrollo.log"),
    "maxBytes": 5 * 1024 * 1024,
    "backupCount": 3,
    "formatter": "detallado",
    "encoding": "utf-8",
    "delay": True,
}
LOGGING["root"]["handlers"] = ["consola", "archivo"]
LOGGING["loggers"]["apps"]["handlers"] = ["consola", "archivo"]

# En desarrollo se permite trabajar con la clave de ejemplo del .env.example.
if not env("DJANGO_SECRET_KEY"):  # pragma: no cover - solo conveniencia local
    SECRET_KEY = "clave-solo-para-desarrollo-local-no-usar-en-produccion"  # noqa: S105
