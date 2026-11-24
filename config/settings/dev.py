"""Configuración para desarrollo local."""

from .base import *  # noqa: F403

DEBUG = env.bool("DJANGO_DEBUG", default=True)  # noqa: F405
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-do-not-deploy"  # noqa: F405
