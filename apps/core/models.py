"""Modelos compartidos: sucursales, parámetros, secuencias documentales e idempotencia.

Reglas de diseño que se respetan en todo el proyecto:

* Los montos son ``Decimal``; el sistema nunca usa ``float``.
* Las claves foráneas de tablas financieras usan ``PROTECT`` (nunca ``CASCADE``).
* Las secuencias documentales se incrementan con bloqueo de fila para que no existan
  huecos ni números repetidos.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from .exceptions import ErrorDeConfiguracion, ErrorDeValidacion


class ModeloBase(models.Model):
    """Campos de trazabilidad temporal presentes en todas las tablas."""

    creado_en = models.DateTimeField("creado en", auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        abstract = True


class Sucursal(ModeloBase):
    """Oficina de la cooperativa. Hoy hay una sola, con caja centralizada."""

    codigo = models.CharField(
        "código",
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9\-]{2,10}$",
                message="Use de 2 a 10 caracteres en mayúsculas, números o guiones.",
            )
        ],
    )
    nombre = models.CharField("nombre", max_length=120)
    direccion = models.CharField("dirección", max_length=250, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "sucursal"
        verbose_name_plural = "sucursales"
        ordering = ["codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} · {self.nombre}"


class Moneda(ModeloBase):
    """Moneda del sistema. En esta fase solo se usa DOP; el modelo admite otras."""

    codigo = models.CharField("código ISO", max_length=3, unique=True)
    nombre = models.CharField("nombre", max_length=60)
    simbolo = models.CharField("símbolo", max_length=5)
    decimales = models.PositiveSmallIntegerField("decimales", default=2)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "moneda"
        verbose_name_plural = "monedas"
        ordering = ["codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} ({self.simbolo})"


class Feriado(ModeloBase):
    """Día no laborable, usado para calcular fechas de vencimiento de cuotas."""

    fecha = models.DateField("fecha", unique=True)
    descripcion = models.CharField("descripción", max_length=120)

    class Meta:
        verbose_name = "feriado"
        verbose_name_plural = "feriados"
        ordering = ["fecha"]

    def __str__(self) -> str:
        return f"{self.fecha:%d/%m/%Y} · {self.descripcion}"


class ParametroSistema(ModeloBase):
    """Parámetro configurable del sistema.

    Todo valor que la cooperativa pueda cambiar sin desplegar código vive aquí: umbrales,
    días de gracia, tasas por defecto e interruptores como la emisión de NCF.
    """

    class TipoDato(models.TextChoices):
        TEXTO = "TEXTO", "Texto"
        ENTERO = "ENTERO", "Número entero"
        DECIMAL = "DECIMAL", "Número decimal"
        BOOLEANO = "BOOLEANO", "Sí o no"
        JSON = "JSON", "Estructura JSON"

    clave = models.CharField("clave", max_length=80, unique=True)
    valor = models.TextField("valor", blank=True)
    tipo_dato = models.CharField(
        "tipo de dato", max_length=10, choices=TipoDato.choices, default=TipoDato.TEXTO
    )
    descripcion = models.CharField("descripción", max_length=250, blank=True)
    editable = models.BooleanField(
        "editable desde la interfaz",
        default=True,
        help_text="Desactive para parámetros que solo debe cambiar un administrador técnico.",
    )

    class Meta:
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ["clave"]
        permissions = [
            ("puede_gestionar_parametros", "Puede gestionar los parámetros del sistema"),
        ]

    def __str__(self) -> str:
        return self.clave

    def clean(self) -> None:
        """Valida que el valor sea convertible al tipo declarado."""
        super().clean()
        try:
            self.valor_convertido()
        except (ErrorDeValidacion, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
            raise ErrorDeValidacion(
                f"El valor «{self.valor}» no corresponde al tipo {self.get_tipo_dato_display()}."
            ) from exc

    def valor_convertido(self) -> Any:
        """Devuelve el valor ya convertido a su tipo.

        Raises:
            ErrorDeValidacion: si el texto almacenado no es convertible.
        """
        crudo = (self.valor or "").strip()
        if self.tipo_dato == self.TipoDato.ENTERO:
            return int(crudo)
        if self.tipo_dato == self.TipoDato.DECIMAL:
            return Decimal(crudo)
        if self.tipo_dato == self.TipoDato.BOOLEANO:
            return crudo.lower() in {"1", "true", "verdadero", "si", "sí", "yes"}
        if self.tipo_dato == self.TipoDato.JSON:
            return json.loads(crudo or "{}")
        return self.valor


class SecuenciaDocumental(ModeloBase):
    """Consecutivo de documentos (comprobantes, recibos, asientos).

    El número se obtiene bloqueando la fila, de modo que dos cajeros concurrentes nunca
    reciben el mismo número ni se generan huecos.
    """

    tipo = models.CharField("tipo de documento", max_length=40)
    prefijo = models.CharField("prefijo", max_length=10, blank=True)
    longitud = models.PositiveSmallIntegerField(
        "longitud del consecutivo", default=6, validators=[MinValueValidator(1)]
    )
    siguiente = models.PositiveBigIntegerField("próximo número", default=1)
    sucursal = models.ForeignKey(
        Sucursal,
        verbose_name="sucursal",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="secuencias",
        help_text="Vacío para una secuencia compartida por todas las sucursales.",
    )
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "secuencia documental"
        verbose_name_plural = "secuencias documentales"
        ordering = ["tipo", "sucursal"]
        constraints = [
            # En PostgreSQL un índice único con NULL admite varios NULL, por eso se
            # separa el caso "con sucursal" del caso "global".
            models.UniqueConstraint(
                fields=["tipo", "sucursal"],
                condition=models.Q(sucursal__isnull=False),
                name="uq_secuencia_tipo_sucursal",
            ),
            models.UniqueConstraint(
                fields=["tipo"],
                condition=models.Q(sucursal__isnull=True),
                name="uq_secuencia_tipo_global",
            ),
        ]

    def __str__(self) -> str:
        ambito = self.sucursal.codigo if self.sucursal_id else "global"
        return f"{self.tipo} ({ambito})"

    def formatear(self, numero: int) -> str:
        """Compone el número visible, por ejemplo ``REC-000123``."""
        return f"{self.prefijo}{numero:0{self.longitud}d}"


class OperacionIdempotente(models.Model):
    """Registro de operaciones ya ejecutadas.

    Evita el doble posteo cuando el usuario hace doble clic o reintenta una petición
    HTMX. La clave la genera el formulario y viaja con la petición.
    """

    clave = models.UUIDField("clave", primary_key=True, default=uuid.uuid4, editable=False)
    modulo = models.CharField("módulo", max_length=40)
    operacion = models.CharField("operación", max_length=60)
    resultado_id = models.BigIntegerField("identificador del resultado", null=True, blank=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "operación idempotente"
        verbose_name_plural = "operaciones idempotentes"
        ordering = ["-creado_en"]

    def __str__(self) -> str:
        return f"{self.modulo}.{self.operacion} [{self.clave}]"


def validar_monto_no_negativo(valor: Decimal) -> None:
    """Comprueba que un monto no sea negativo.

    Raises:
        ErrorDeValidacion: si el monto es negativo.
    """
    if valor < Decimal("0"):
        raise ErrorDeValidacion("El monto no puede ser negativo.")
    if not isinstance(valor, Decimal):
        raise ErrorDeValidacion("Todo monto debe expresarse con Decimal, nunca con float.")


def exigir_configuracion(valor: Any, mensaje: str) -> Any:
    """Falla con un mensaje claro cuando falta una configuración obligatoria.

    Raises:
        ErrorDeConfiguracion: si el valor es nulo, vacío o cero.
    """
    # No se usa ``valor in {"", 0}``: el valor podría ser una lista o un diccionario,
    # que no son hashables y harían fallar la comprobación.
    if valor is None or valor == "" or valor == 0:  # noqa: PLR1714
        raise ErrorDeConfiguracion(mensaje)
    return valor
