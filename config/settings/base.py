"""Configuración común a todos los entornos de COOPGESTION.

Los secretos y los parámetros que cambian entre entornos se leen del archivo ``.env``
(ver ``.env.example``). Nada sensible vive en el repositorio.
"""

from __future__ import annotations

from pathlib import Path

import environ

# config/settings/base.py -> config/settings -> config -> raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, ""),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, "postgres://coopgestion:coopgestion_dev@127.0.0.1:5433/coopgestion"),
    DB_CONN_MAX_AGE=(int, 60),
    EMAIL_URL=(str, "consolemail://"),
    LOG_LEVEL=(str, "INFO"),
    # Interruptor fiscal: no se emite ningún comprobante NCF mientras esté en falso
    # (decisión D-08; requiere RNC y autorización de la DGII).
    EMISION_NCF_ACTIVA=(bool, False),
    # Seguridad de acceso
    INTENTOS_LOGIN=(int, 5),
    MINUTOS_BLOQUEO=(int, 15),
    SEGUNDOS_INACTIVIDAD_SESION=(int, 1800),
    # Umbral de doble aprobación (decisión D-07)
    UMBRAL_RETIRO_DOBLE_FIRMA=(str, "50000.00"),
)

# Se lee .env si existe; en producción las variables vienen del entorno del contenedor.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

# --------------------------------------------------------------------------- #
# Aplicaciones
# --------------------------------------------------------------------------- #
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

APPS_PROPIAS = [
    "apps.core",
    "apps.usuarios",
    "apps.auditoria",
]

INSTALLED_APPS = DJANGO_APPS + APPS_PROPIAS

# django-q2 se activa en la Fase 4, cuando existan tareas programadas de intereses.

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Debe ir después de AuthenticationMiddleware: necesita request.user.
    "apps.auditoria.middleware.ContextoAuditoriaMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navegacion",
            ],
        },
    },
]

# --------------------------------------------------------------------------- #
# Base de datos
# --------------------------------------------------------------------------- #
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env("DB_CONN_MAX_AGE")
DATABASES["default"]["ATOMIC_REQUESTS"] = False  # la atomicidad la controla services.py
DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------- #
# Autenticación
# --------------------------------------------------------------------------- #
AUTH_USER_MODEL = "usuarios.Usuario"

#: Los permisos se resuelven desde el rol del usuario, no desde sus grupos de Django.
AUTHENTICATION_BACKENDS = ["apps.usuarios.backends.BackendRoles"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LOGIN_URL = "/cuentas/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/cuentas/login/"

# --------------------------------------------------------------------------- #
# Sesiones: expiración por inactividad, no por tiempo absoluto
# --------------------------------------------------------------------------- #
SESSION_COOKIE_AGE = env("SEGUNDOS_INACTIVIDAD_SESION")
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # HTMX necesita leer el token desde el formulario
CSRF_COOKIE_SAMESITE = "Lax"

# --------------------------------------------------------------------------- #
# Internacionalización: todo en español, moneda DOP
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "es-do"
TIME_ZONE = "America/Santo_Domingo"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --------------------------------------------------------------------------- #
# Archivos estáticos y multimedia
# --------------------------------------------------------------------------- #
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --------------------------------------------------------------------------- #
# Correo
# --------------------------------------------------------------------------- #
EMAIL_CONFIG = env.email_url("EMAIL_URL")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="COOPGESTION <no-responder@coopgestion.local>"
)

# --------------------------------------------------------------------------- #
# Parámetros propios del negocio
# --------------------------------------------------------------------------- #
COOPGESTION = {
    "NOMBRE": env("COOPGESTION_NOMBRE", default="COOPGESTION"),
    "MONEDA": "DOP",
    "SIMBOLO_MONEDA": "RD$",
    "EMISION_NCF_ACTIVA": env("EMISION_NCF_ACTIVA"),
    "INTENTOS_LOGIN": env("INTENTOS_LOGIN"),
    "MINUTOS_BLOQUEO": env("MINUTOS_BLOQUEO"),
    "UMBRAL_RETIRO_DOBLE_FIRMA": env("UMBRAL_RETIRO_DOBLE_FIRMA"),
}

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# --------------------------------------------------------------------------- #
# Registro de eventos
# --------------------------------------------------------------------------- #
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detallado": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "detallado",
        },
    },
    "root": {"handlers": ["consola"], "level": env("LOG_LEVEL")},
    "loggers": {
        "django.security": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["consola"], "level": env("LOG_LEVEL"), "propagate": False},
    },
}
