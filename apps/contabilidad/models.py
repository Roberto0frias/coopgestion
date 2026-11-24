from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class PeriodoContable(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"

    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.ABIERTO)
    abierto_en = models.DateTimeField(default=timezone.now)
    cerrado_en = models.DateTimeField(null=True, blank=True)
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="periodos_contables_cerrados",
    )
    ultimo_numero_asiento = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-anio", "-mes")
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=("anio", "mes"), name="periodo_anio_mes_uk"),
            models.CheckConstraint(
                condition=Q(mes__gte=1, mes__lte=12), name="periodo_mes_rango_ck"
            ),
            models.CheckConstraint(condition=Q(anio__gte=2000), name="periodo_anio_minimo_ck"),
        ]
        verbose_name = "período contable"
        verbose_name_plural = "períodos contables"

    def __str__(self) -> str:
        return f"{self.anio}-{self.mes:02d} · {self.get_estado_display()}"


class CuentaContable(models.Model):
    class Grupo(models.TextChoices):
        ACTIVO = "1", "1 · Activo"
        PASIVO = "2", "2 · Pasivo"
        PATRIMONIO = "3", "3 · Patrimonio"
        INGRESOS = "4", "4 · Ingresos"
        GASTOS = "5", "5 · Costos y gastos"
        ORDEN = "6", "6 · Cuentas de orden"

    class Naturaleza(models.TextChoices):
        DEUDORA = "DEUDORA", "Deudora"
        ACREEDORA = "ACREEDORA", "Acreedora"

    codigo = models.CharField(max_length=24, unique=True)
    nombre = models.CharField(max_length=180)
    grupo = models.CharField(max_length=1, choices=Grupo.choices)
    naturaleza = models.CharField(max_length=10, choices=Naturaleza.choices)
    nivel = models.PositiveSmallIntegerField(default=4)
    cuenta_padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subcuentas",
        null=True,
        blank=True,
    )
    permite_movimiento = models.BooleanField(default=True)
    es_efectivo = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("codigo",)
        verbose_name = "cuenta contable"
        verbose_name_plural = "cuentas contables"
        constraints = [  # noqa: RUF012
            models.CheckConstraint(condition=~Q(codigo=""), name="cuenta_codigo_no_vacio_ck"),
            models.CheckConstraint(condition=~Q(nombre=""), name="cuenta_nombre_no_vacio_ck"),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} · {self.nombre}"

    def clean(self) -> None:
        super().clean()
        if self.codigo and not all(
            segmento.isascii() and segmento.isdecimal() for segmento in self.codigo.split("-")
        ):
            raise ValidationError({"codigo": "Usa segmentos numéricos separados por guiones."})
        if self.codigo and self.grupo != self.codigo.split("-", maxsplit=1)[0]:
            raise ValidationError(
                {"grupo": "El grupo debe coincidir con el primer dígito del código."}
            )
        if self.codigo:
            esperado = len(self.codigo.split("-"))
            if self.nivel != esperado:
                raise ValidationError({"nivel": f"El código tiene {esperado} segmentos."})
        if self.cuenta_padre_id:
            prefijo = self.codigo.rsplit("-", maxsplit=1)[0]
            if not self.codigo.startswith(f"{self.cuenta_padre.codigo}-"):
                raise ValidationError(
                    {"cuenta_padre": "La cuenta debe quedar bajo su prefijo contable."}
                )
            if self.cuenta_padre.codigo != prefijo:
                raise ValidationError(
                    {"cuenta_padre": "La cuenta padre debe ser el nivel anterior inmediato."}
                )
            if self.cuenta_padre.permite_movimiento:
                raise ValidationError(
                    {"cuenta_padre": "Una cuenta padre no puede recibir movimientos."}
                )


class Asiento(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        REVERSADO = "REVERSADO", "Reversado"

    numero = models.CharField(max_length=24, unique=True, null=True, blank=True)
    fecha = models.DateField(default=timezone.localdate, db_index=True)
    descripcion = models.CharField(max_length=255)
    periodo = models.ForeignKey(PeriodoContable, on_delete=models.PROTECT, related_name="asientos")
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    origen_app = models.CharField(max_length=64, blank=True)
    origen_tipo = models.CharField(max_length=64, blank=True)
    origen_id = models.CharField(max_length=64, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asientos_creados",
    )
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asientos_confirmados",
        null=True,
        blank=True,
    )
    confirmado_en = models.DateTimeField(null=True, blank=True)
    total_debito = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_credito = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    clave_idempotencia = models.UUIDField(unique=True)
    reversa_de = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="asiento_reverso",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-fecha", "-id")
        verbose_name = "asiento contable"
        verbose_name_plural = "asientos contables"
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=Q(estado="BORRADOR")
                | Q(
                    total_debito__gt=0,
                    total_credito=F("total_debito"),
                    confirmado_por__isnull=False,
                    confirmado_en__isnull=False,
                    numero__isnull=False,
                ),
                name="asiento_confirmado_balanceado_ck",
            ),
        ]

    def __str__(self) -> str:
        return self.numero or f"Borrador #{self.pk or 'nuevo'}"

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            anterior = (
                type(self).objects.filter(pk=self.pk).values_list("estado", flat=True).first()
            )
            if anterior in (self.Estado.CONFIRMADO, self.Estado.REVERSADO):
                raise ValidationError("Un asiento confirmado no se puede modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estado != self.Estado.BORRADOR:
            raise ValidationError("Solo se puede borrar un borrador contable.")
        return super().delete(*args, **kwargs)


class SolicitudReverso(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    asiento = models.ForeignKey(
        Asiento, on_delete=models.PROTECT, related_name="solicitudes_reverso"
    )
    motivo = models.TextField()
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reversos_solicitados",
    )
    solicitado_en = models.DateTimeField(default=timezone.now)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reversos_resueltos",
        null=True,
        blank=True,
    )
    resuelto_en = models.DateTimeField(null=True, blank=True)
    asiento_reverso = models.OneToOneField(
        Asiento,
        on_delete=models.PROTECT,
        related_name="solicitud_aprobada",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-solicitado_en", "-id")
        verbose_name = "solicitud de reverso"
        verbose_name_plural = "solicitudes de reverso"

    def __str__(self) -> str:
        return f"Reverso de {self.asiento} · {self.get_estado_display()}"


class LineaAsiento(models.Model):
    asiento = models.ForeignKey(Asiento, on_delete=models.PROTECT, related_name="lineas")
    numero_linea = models.PositiveSmallIntegerField()
    cuenta = models.ForeignKey(
        CuentaContable, on_delete=models.PROTECT, related_name="lineas_asiento"
    )
    descripcion = models.CharField(max_length=180, blank=True)
    debito = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    credito = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        ordering = ("numero_linea",)
        verbose_name = "línea de asiento"
        verbose_name_plural = "líneas de asiento"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("asiento", "numero_linea"), name="asiento_linea_numero_uk"
            ),
            models.CheckConstraint(
                condition=(Q(debito__gt=0, credito=0) | Q(debito=0, credito__gt=0)),
                name="asiento_linea_un_solo_lado_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.asiento} · línea {self.numero_linea}"

    def save(self, *args, **kwargs) -> None:
        if self.asiento_id and self.asiento.estado != Asiento.Estado.BORRADOR:
            raise ValidationError("Las líneas de un asiento confirmado son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.asiento.estado != Asiento.Estado.BORRADOR:
            raise ValidationError("Las líneas de un asiento confirmado no se pueden borrar.")
        return super().delete(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.asiento_id and self.asiento.estado != Asiento.Estado.BORRADOR:
            raise ValidationError("No se pueden añadir líneas a un asiento confirmado.")
        if self.cuenta_id and (not self.cuenta.activa or not self.cuenta.permite_movimiento):
            raise ValidationError("La cuenta está inactiva o no acepta movimientos.")
