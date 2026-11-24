from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class EventoAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        del kwargs
        raise ValidationError("Los eventos de auditoría son inmutables.")

    def delete(self):
        raise ValidationError("Los eventos de auditoría no se pueden borrar.")

    def bulk_update(self, objs, fields, batch_size=None):
        del objs, fields, batch_size
        raise ValidationError("Los eventos de auditoría son inmutables.")

    def bulk_create(self, objs, **kwargs):
        del objs, kwargs
        raise ValidationError("Use el servicio de auditoría para registrar eventos.")


class EstadoCadena(models.Model):
    """Punto de serialización para mantener una sola cadena de auditoría."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    ultimo_hash = models.CharField(max_length=64, blank=True, default="")

    def __str__(self) -> str:
        return "Cadena de auditoría"

    def save(self, *args, **kwargs) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "El estado de auditoría solo puede actualizarse desde el servicio."
            )
        super().save(*args, **kwargs)


class EventoAuditoria(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_auditoria",
        null=True,
        blank=True,
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    accion = models.CharField(max_length=64, db_index=True)
    app = models.CharField(max_length=64, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    objeto_id = models.CharField(max_length=64, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    hash_anterior = models.CharField(max_length=64, blank=True)
    hash_registro = models.CharField(max_length=64, unique=True)
    objects = EventoAuditoriaQuerySet.as_manager()

    class Meta:
        ordering = ("-id",)
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self) -> str:
        return f"{self.accion} · {self.fecha:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValidationError("Los eventos de auditoría son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        del args, kwargs
        raise ValidationError("Los eventos de auditoría no se pueden borrar.")
