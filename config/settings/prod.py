"""Configuración de producción para el VPS Linux con Docker y Nginx.

Requiere HTTPS terminado en Nginx y las variables de entorno definidas en el servidor.
"""

from __future__ import annotations

from .base import *  # noqa: F403
from .base import BASE_DIR, LOGGING, env

DEBUG = False

# Sin clave secreta no se arranca: es preferible fallar a operar de forma insegura.
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:  # pragma: no cover - protección de despliegue
    raise RuntimeError("DJANGO_SECRET_KEY es obligatoria en producción.")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:  # pragma: no cover - protección de despliegue
    raise RuntimeError("DJANGO_ALLOWED_HOSTS es obligatoria en producción.")

# --------------------------------------------------------------------------- #
# HTTPS y cabeceras de seguridad
# --------------------------------------------------------------------------- #
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000  # un año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------- #
# Archivos estáticos y multimedia servidos por Nginx
# --------------------------------------------------------------------------- #
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------------------------------- #
# Registro a archivo, con rotación
# --------------------------------------------------------------------------- #
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

LOGGING["handlers"]["archivo"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(BASE_DIR / "logs" / "produccion.log"),
    "maxBytes": 20 * 1024 * 1024,
    "backupCount": 10,
    "formatter": "detallado",
    "encoding": "utf-8",
}
LOGGING["root"]["handlers"] = ["consola", "archivo"]
LOGGING["loggers"]["apps"]["handlers"] = ["consola", "archivo"]
LOGGING["loggers"]["django.request"] = {
    "handlers": ["consola", "archivo"],
    "level": "ERROR",
    "propagate": False,
}
