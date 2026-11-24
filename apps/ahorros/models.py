from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.socios.models import Socio


class ProductoAhorro(models.Model):
    class TipoSocio(models.TextChoices):
        PLENO = "PLENO", "Socio pleno"
        AHORRANTE = "AHORRANTE", "Socio ahorrante"

    nombre = models.CharField(max_length=120, unique=True)
    tipo_socio = models.CharField(max_length=12, choices=TipoSocio.choices)
    tasa_anual = models.DecimalField(
        max_digits=7,
        decimal_places=5,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Fracción anual; requiere aprobación de Administración.",
    )
    base_dias = models.PositiveSmallIntegerField(default=360)
    activa = models.BooleanField(default=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_ahorro_creados",
    )
    creada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "producto de ahorro"
        verbose_name_plural = "productos de ahorro"
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=Q(base_dias__in=(360, 365)), name="producto_ahorro_base_dias_ck"
            ),
            models.CheckConstraint(
                condition=Q(activa=False) | Q(tasa_anual__isnull=False),
                name="producto_ahorro_activo_con_tasa_ck",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        if self.activa and self.tasa_anual is None:
            raise ValidationError(
                {"tasa_anual": "Define y aprueba la tasa antes de activar el producto."}
            )


class CuentaAhorro(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"
        CERRADA = "CERRADA", "Cerrada"

    numero = models.CharField(max_length=20, unique=True, blank=True)
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name="cuentas_ahorro")
    producto = models.ForeignKey(ProductoAhorro, on_delete=models.PROTECT, related_name="cuentas")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA)
    abierta_en = models.DateTimeField(default=timezone.now)
    abierta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cuentas_ahorro_abiertas",
    )

    class Meta:
        ordering = ("numero",)
        verbose_name = "cuenta de ahorro"
        verbose_name_plural = "cuentas de ahorro"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("socio", "producto"), name="cuenta_ahorro_socio_producto_uk"
            ),
        ]

    def __str__(self):
        return self.numero or f"Cuenta nueva · {self.socio.codigo}"

    def clean(self):
        super().clean()
        if self.socio_id and self.socio.estado != Socio.Estado.ACTIVO:
            raise ValidationError({"socio": "Solo se puede abrir una cuenta a un socio admitido."})
        if self.socio_id and self.producto_id and self.socio.tipo != self.producto.tipo_socio:
            raise ValidationError({"producto": "El producto no corresponde al tipo de socio."})
        if self.estado == self.Estado.ACTIVA and self.producto_id and not self.producto.activa:
            raise ValidationError(
                {"producto": "El producto está inactivo y no admite cuentas nuevas."}
            )
