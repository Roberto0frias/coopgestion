"""Modelos de usuarios, roles y control de acceso.

El sistema de permisos se apoya en el marco de Django: cada ``Rol`` tiene asignados
permisos reales (``auth.Permission``) y el usuario hereda los de su rol. No se usan los
``Group`` de Django para no duplicar la fuente de verdad; los permisos se gestionan
exclusivamente desde la matriz declarada en :mod:`apps.usuarios.permisos`.
"""

from __future__ import annotations

from typing import Any, ClassVar

from apps.core.models import ModeloBase, Sucursal
from apps.core.validators import limpiar_cedula
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Permission, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

VALIDADOR_USUARIO = RegexValidator(
    regex=r"^[a-zA-Z0-9._-]{4,50}$",
    message="Use de 4 a 50 caracteres: letras, números, punto, guion o guion bajo.",
)
VALIDADOR_CEDULA = RegexValidator(
    regex=r"^\d{11}$",
    message="La cédula debe tener 11 dígitos, sin guiones.",
)


class Rol(ModeloBase):
    """Perfil de acceso. Agrupa los permisos que puede ejecutar un usuario."""

    codigo = models.CharField(
        "código",
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z_]{3,20}$",
                message="Use de 3 a 20 caracteres en mayúsculas y guion bajo.",
            )
        ],
    )
    nombre = models.CharField("nombre", max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    es_solo_lectura = models.BooleanField(
        "solo lectura",
        default=False,
        help_text="El rol no puede ejecutar ninguna operación que modifique datos.",
    )
    orden = models.PositiveSmallIntegerField("orden de presentación", default=100)
    activo = models.BooleanField("activo", default=True)
    permisos = models.ManyToManyField(
        Permission,
        verbose_name="permisos",
        blank=True,
        related_name="roles",
        help_text="Permisos de Django que otorga este rol.",
    )

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["orden", "codigo"]
        permissions = [
            ("puede_gestionar_usuarios", "Puede gestionar usuarios y roles"),
            ("puede_restablecer_password", "Puede restablecer la contraseña de otro usuario"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo})"

    @property
    def cantidad_permisos(self) -> int:
        return self.permisos.count()


class UsuarioManager(BaseUserManager["Usuario"]):
    """Gestor del modelo de usuario personalizado."""

    use_in_migrations = True

    def _crear(self, username: str, email: str, password: str | None, **extra: Any) -> Usuario:
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        usuario = self.model(
            username=username.strip(),
            email=self.normalize_email(email).lower(),
            **extra,
        )
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(  # type: ignore[override]
        self, username: str, email: str, password: str | None = None, **extra: Any
    ) -> Usuario:
        """Crea un usuario interno con contraseña cifrada."""
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(username, email, password, **extra)

    def create_superuser(  # type: ignore[override]
        self, username: str, email: str, password: str | None = None, **extra: Any
    ) -> Usuario:
        """Crea un superusuario; no depende de ningún rol."""
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")
        return self._crear(username, email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin, ModeloBase):
    """Usuario interno de la cooperativa.

    No hay acceso para socios: esta fase es exclusivamente para el personal.
    """

    username = models.CharField(
        "usuario",
        max_length=50,
        unique=True,
        validators=[VALIDADOR_USUARIO],
        help_text="Se usa para iniciar sesión.",
    )
    email = models.EmailField("correo electrónico", unique=True)
    nombres = models.CharField("nombres", max_length=80)
    apellidos = models.CharField("apellidos", max_length=80)
    cedula = models.CharField(
        "cédula",
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        validators=[VALIDADOR_CEDULA],
        help_text="11 dígitos, sin guiones.",
    )
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    rol = models.ForeignKey(
        Rol,
        verbose_name="rol",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    sucursal = models.ForeignKey(
        Sucursal,
        verbose_name="sucursal",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )

    is_active = models.BooleanField(
        "activo",
        default=True,
        help_text="Desactive en lugar de eliminar: el historial debe conservarse.",
    )
    is_staff = models.BooleanField(
        "acceso al panel de administración",
        default=False,
        help_text="Solo para el personal técnico o el administrador del sistema.",
    )
    debe_cambiar_password = models.BooleanField("debe cambiar la contraseña", default=True)
    intentos_fallidos = models.PositiveSmallIntegerField("intentos fallidos", default=0)
    bloqueado_hasta = models.DateTimeField("bloqueado hasta", null=True, blank=True)
    ultimo_acceso = models.DateTimeField("último acceso", null=True, blank=True)

    objects: ClassVar[UsuarioManager] = UsuarioManager()  # type: ignore[assignment]

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "nombres", "apellidos"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombres", "apellidos"]
        indexes = [models.Index(fields=["rol", "is_active"], name="ix_usuario_rol_activo")]

    def __str__(self) -> str:
        return f"{self.nombre_completo} ({self.username})"

    # ------------------------------------------------------------------ #
    # Presentación
    # ------------------------------------------------------------------ #
    @property
    def nombre_completo(self) -> str:
        """Nombre y apellidos del usuario."""
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def nombre_corto(self) -> str:
        """Nombre corto para la barra de navegación."""
        return (
            f"{self.nombres.split()[0]} {self.apellidos.split()[0]}"
            if self.apellidos
            else self.nombres
        )

    # ------------------------------------------------------------------ #
    # Estado de seguridad
    # ------------------------------------------------------------------ #
    @property
    def esta_bloqueado(self) -> bool:
        """Indica si la cuenta está bloqueada temporalmente por intentos fallidos."""
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    @property
    def es_solo_lectura(self) -> bool:
        """Indica si el rol del usuario es de solo lectura."""
        return bool(self.rol and self.rol.es_solo_lectura)

    @property
    def puede_aprobar(self) -> bool:
        """Indica si el usuario puede otorgar la segunda firma (decisión D-07)."""
        from .permisos import usuario_puede_aprobar

        return usuario_puede_aprobar(self)

    # ------------------------------------------------------------------ #
    # Permisos: la fuente es el rol, no los grupos de Django
    # ------------------------------------------------------------------ #
    def get_user_permissions(self, obj: Any = None) -> set[str]:
        """Permisos otorgados por el rol del usuario."""
        if not self.is_active or self.rol_id is None:
            return set()
        if not self.rol.activo:
            return set()
        return {
            f"{permiso.content_type.app_label}.{permiso.codename}"
            for permiso in self.rol.permisos.select_related("content_type")
        }

    def get_group_permissions(self, obj: Any = None) -> set[str]:
        """No se usan grupos de Django: los permisos vienen del rol."""
        return set()

    def tiene_permiso(self, codigo: str) -> bool:
        """Comprueba un permiso concreto, por ejemplo ``usuarios.view_usuario``."""
        return self.has_perm(codigo)

    def limpiar_cedula(self) -> None:
        """Normaliza la cédula quitando guiones."""
        if self.cedula:
            self.cedula = limpiar_cedula(self.cedula)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.limpiar_cedula()
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)


class IntentoAcceso(ModeloBase):
    """Bitácora de intentos de inicio de sesión.

    Permite detectar ataques de fuerza bruta y queda como evidencia para el Auditor.
    """

    usuario = models.ForeignKey(
        Usuario,
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="intentos_acceso",
    )
    username_intentado = models.CharField("usuario intentado", max_length=50, blank=True)
    fecha = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    user_agent = models.CharField("navegador", max_length=250, blank=True)
    exitoso = models.BooleanField("exitoso", default=False)
    motivo_fallo = models.CharField("motivo del fallo", max_length=120, blank=True)

    class Meta:
        verbose_name = "intento de acceso"
        verbose_name_plural = "intentos de acceso"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["username_intentado", "fecha"], name="ix_intento_usuario_fecha"),
            models.Index(fields=["ip", "fecha"], name="ix_intento_ip_fecha"),
        ]

    def __str__(self) -> str:
        estado = "correcto" if self.exitoso else f"fallido ({self.motivo_fallo})"
        return f"{self.fecha:%d/%m/%Y %H:%M} · {self.username_intentado} · {estado}"
