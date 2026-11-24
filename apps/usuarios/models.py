from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class AdministradorUsuarios(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("rol", "ADMIN")
        return super().create_superuser(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        CONTADOR = "CONTADOR", "Contador"
        OFICIAL = "OFICIAL", "Oficial de Préstamos"
        CAJERO = "CAJERO", "Cajero"
        AUDITOR = "AUDITOR", "Auditor"
        COMITE = "COMITE", "Gerencia / Comité de Crédito"

    email = models.EmailField("correo electrónico", unique=True)
    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.OFICIAL, db_index=True)
    debe_cambiar_password = models.BooleanField(default=False)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    objects = AdministradorUsuarios()

    class Meta:
        ordering = ("last_name", "first_name", "username")
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    def tiene_rol(self, *roles: str) -> bool:
        return self.is_superuser or self.rol in roles

    @property
    def es_solo_lectura(self) -> bool:
        return self.rol == self.Rol.AUDITOR and not self.is_superuser
