from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Socio(models.Model):
    class Tipo(models.TextChoices):
        PLENO = "PLENO", "Socio pleno"
        AHORRANTE = "AHORRANTE", "Socio ahorrante"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de admisión"
        ACTIVO = "ACTIVO", "Activo"
        RECHAZADO = "RECHAZADO", "Admisión rechazada"
        RETIRADO = "RETIRADO", "Retirado"

    class EstadoCivil(models.TextChoices):
        SOLTERO = "SOLTERO", "Soltero/a"
        CASADO = "CASADO", "Casado/a"
        UNION_LIBRE = "UNION_LIBRE", "Unión libre"
        DIVORCIADO = "DIVORCIADO", "Divorciado/a"
        VIUDO = "VIUDO", "Viudo/a"
        NO_INFORMADO = "NO_INFORMADO", "No informado"

    class NivelRiesgo(models.TextChoices):
        BAJO = "BAJO", "Bajo"
        MEDIO = "MEDIO", "Medio"
        ALTO = "ALTO", "Alto"
        PENDIENTE = "PENDIENTE", "Pendiente de evaluación"

    codigo = models.CharField(max_length=16, unique=True, blank=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    es_voluntaria_proyecto = models.BooleanField(default=False)
    proyecto = models.CharField(max_length=160, blank=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    estado_civil = models.CharField(
        max_length=16, choices=EstadoCivil.choices, default=EstadoCivil.NO_INFORMADO
    )
    ocupacion = models.CharField(max_length=120, blank=True)
    ingresos_mensuales = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    fecha_ingreso = models.DateField(default=timezone.localdate)
    fecha_retiro = models.DateField(null=True, blank=True)
    motivo_retiro = models.TextField(blank=True)
    es_pep = models.BooleanField(default=False)
    nivel_riesgo = models.CharField(
        max_length=12, choices=NivelRiesgo.choices, default=NivelRiesgo.PENDIENTE
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="socios_registrados",
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="socios_aprobados",
        null=True,
        blank=True,
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)

    class Meta:
        ordering = ("apellidos", "nombres", "id")
        verbose_name = "socio"
        verbose_name_plural = "socios"
        indexes = [  # noqa: RUF012
            models.Index(fields=("estado", "apellidos", "nombres"), name="socio_estado_nombre_idx"),
        ]
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=Q(aprobado_por__isnull=True) | ~Q(aprobado_por=F("creado_por")),
                name="socio_aprobador_distinto_creador_ck",
            ),
            models.CheckConstraint(
                condition=Q(es_voluntaria_proyecto=False) | Q(tipo="AHORRANTE", proyecto__gt=""),
                name="socio_voluntaria_requiere_ahorrante_proyecto_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} · {self.nombres} {self.apellidos}"

    def save(self, *args, **kwargs) -> None:
        self.cedula = "".join(self.cedula.upper().split()).replace("-", "")
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.fecha_nacimiento and self.fecha_nacimiento >= timezone.localdate():
            raise ValidationError(
                {"fecha_nacimiento": "La fecha de nacimiento debe ser anterior a hoy."}
            )
        if self.es_voluntaria_proyecto:
            if self.tipo != self.Tipo.AHORRANTE:
                raise ValidationError(
                    {"tipo": "Las voluntarias de proyectos se registran como socios ahorrantes."}
                )
            if not self.proyecto.strip():
                raise ValidationError({"proyecto": "Indica el proyecto social asociado."})
        elif self.proyecto.strip():
            raise ValidationError(
                {"proyecto": "El proyecto solo aplica a voluntarias de proyectos sociales."}
            )
        if self.aprobado_por_id and self.aprobado_por_id == self.creado_por_id:
            raise ValidationError("Quien registra al socio no puede aprobar su propia admisión.")
