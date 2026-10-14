"""Configuración para la ejecución de pruebas automatizadas.

Se usa un hash de contraseña rápido porque las pruebas crean muchos usuarios; la
seguridad de las contraseñas reales se verifica en ``config.settings.prod``.
"""

from __future__ import annotations

from .base import *  # noqa: F403
from .base import LOGGING

DEBUG = False

# Clave fija y pública: solo existe para firmar sesiones durante las pruebas.
SECRET_KEY = "clave-solo-para-pruebas-automatizadas"  # noqa: S105

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Las pruebas de rendimiento de contraseñas no aportan nada aquí.
LOGGING["root"]["level"] = "CRITICAL"
LOGGING["loggers"]["apps"]["level"] = "CRITICAL"

# Acelera la creación de la base de datos de pruebas.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
