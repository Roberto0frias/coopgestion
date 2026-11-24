"""Configuración de producción; falla al iniciar si faltan secretos."""

from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY or SECRET_KEY.startswith("replace-"):  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY es obligatorio en producción.")
if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("Configure DJANGO_ALLOWED_HOSTS en producción.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
