"""Comando de puesta en marcha inicial de COOPGESTION.

Crea la sucursal, la moneda, los parámetros, las secuencias documentales y los roles, y
opcionalmente el primer usuario administrador.

Uso:
    python manage.py sembrar_datos_iniciales
    python manage.py sembrar_datos_iniciales --admin-username roberto \\
        --admin-email friasdelarosa0@gmail.com --admin-password "ClaveTemporal123"
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import (
    Moneda,
    ParametroSistema,
    Sucursal,
)
from apps.core.services import asegurar_secuencia, fijar_parametro

#: Parámetros iniciales. La tasa de interés de ahorro NO se crea a propósito: queda
#: pendiente (P-04) hasta que la administración la defina, y el cálculo de intereses
#: fallará con un mensaje claro mientras no exista.
PARAMETROS_INICIALES: list[dict] = [
    {
        "clave": "UMBRAL_RETIRO_DOBLE_FIRMA",
        "valor": "50000.00",
        "tipo": ParametroSistema.TipoDato.DECIMAL,
        "descripcion": "Monto desde el cual un retiro requiere segunda firma (D-07).",
    },
    {
        "clave": "INTENTOS_LOGIN",
        "valor": "5",
        "tipo": ParametroSistema.TipoDato.ENTERO,
        "descripcion": "Intentos fallidos antes de bloquear la cuenta.",
    },
    {
        "clave": "MINUTOS_BLOQUEO",
        "valor": "15",
        "tipo": ParametroSistema.TipoDato.ENTERO,
        "descripcion": "Duración del bloqueo por intentos fallidos, en minutos.",
    },
    {
        "clave": "DIAS_GRACIA_MORA",
        "valor": "3",
        "tipo": ParametroSistema.TipoDato.ENTERO,
        "descripcion": "Días de gracia antes de aplicar mora (D-03).",
    },
    {
        "clave": "PORCENTAJE_MORA_PERIODO",
        "valor": "0.05",
        "tipo": ParametroSistema.TipoDato.DECIMAL,
        "descripcion": "Mora por período de atraso sobre la cuota total (D-03).",
    },
    {
        "clave": "TOPE_MORA",
        "valor": "0.00",
        "tipo": ParametroSistema.TipoDato.DECIMAL,
        "descripcion": "Tope de mora acumulada. 0 significa sin tope (pendiente P-10).",
    },
    {
        "clave": "DIAS_INACTIVIDAD_CUENTA",
        "valor": "180",
        "tipo": ParametroSistema.TipoDato.ENTERO,
        "descripcion": "Días sin movimiento para declarar una cuenta inactiva (P-12).",
    },
    {
        "clave": "EMISION_NCF_ACTIVA",
        "valor": "false",
        "tipo": ParametroSistema.TipoDato.BOOLEANO,
        "descripcion": "Emisión de comprobantes fiscales. Falso hasta tener RNC y DGII (D-08).",
    },
]

#: Secuencias documentales previstas. Se crean ahora para que existan antes de operar.
SECUENCIAS_INICIALES: list[dict] = [
    {"tipo": "DEPOSITO_AHORRO", "prefijo": "DEP-", "longitud": 6},
    {"tipo": "RETIRO_AHORRO", "prefijo": "RET-", "longitud": 6},
    {"tipo": "APORTACION", "prefijo": "APO-", "longitud": 6},
    {"tipo": "PAGO_PRESTAMO", "prefijo": "REC-", "longitud": 6},
    {"tipo": "DESEMBOLSO_PRESTAMO", "prefijo": "DES-", "longitud": 6},
    {"tipo": "ASIENTO_CONTABLE", "prefijo": "AS-", "longitud": 7},
]


class Command(BaseCommand):
    help = (
        "Crea los datos mínimos para operar: sucursal, moneda, parámetros, "
        "secuencias documentales y roles."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--admin-username", default=None)
        parser.add_argument("--admin-email", default=None)
        parser.add_argument("--admin-password", default=None)
        parser.add_argument("--admin-nombres", default="Administrador")
        parser.add_argument("--admin-apellidos", default="COOPGESTION")

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            sucursal = self._sucursal()
            self._moneda()

        self._parametros()
        self._secuencias()
        self.stdout.write("Aplicando la matriz de roles ...")
        call_command("sembrar_roles")

        if options["admin_username"]:
            self._administrador(options, sucursal)

        self.stdout.write(self.style.SUCCESS("Datos iniciales listos."))

    # ------------------------------------------------------------------ #
    def _sucursal(self) -> Sucursal:
        sucursal, creada = Sucursal.objects.get_or_create(
            codigo="CEN",
            defaults={"nombre": "Sucursal Central", "activa": True},
        )
        self.stdout.write(
            self.style.SUCCESS(f"Sucursal {'creada' if creada else 'existente'}: {sucursal}")
        )
        return sucursal

    def _moneda(self) -> Moneda:
        moneda, creada = Moneda.objects.get_or_create(
            codigo="DOP",
            defaults={"nombre": "Peso dominicano", "simbolo": "RD$", "decimales": 2},
        )
        self.stdout.write(
            self.style.SUCCESS(f"Moneda {'creada' if creada else 'existente'}: {moneda}")
        )
        return moneda

    def _parametros(self) -> None:
        for definicion in PARAMETROS_INICIALES:
            parametro = ParametroSistema.objects.filter(clave=definicion["clave"]).first()
            if parametro is None:
                fijar_parametro(
                    definicion["clave"],
                    definicion["valor"],
                    tipo_dato=definicion["tipo"],
                    descripcion=definicion["descripcion"],
                )
                self.stdout.write(self.style.SUCCESS(f"Parámetro creado: {definicion['clave']}"))
            else:
                self.stdout.write(f"Parámetro existente: {definicion['clave']} = {parametro.valor}")

    def _secuencias(self) -> None:
        for definicion in SECUENCIAS_INICIALES:
            asegurar_secuencia(
                definicion["tipo"],
                prefijo=definicion["prefijo"],
                longitud=definicion["longitud"],
                sucursal=None,
            )
        self.stdout.write(
            self.style.SUCCESS(f"Secuencias documentales aseguradas: {len(SECUENCIAS_INICIALES)}")
        )

    def _administrador(self, options: dict, sucursal: Sucursal) -> None:
        from apps.usuarios.models import Rol, Usuario
        from apps.usuarios.services import crear_usuario

        if Usuario.objects.filter(username=options["admin_username"]).exists():
            self.stdout.write(f"El usuario {options['admin_username']} ya existe; no se toca.")
            return

        rol_admin = Rol.objects.get(codigo="ADMIN")
        usuario = crear_usuario(
            username=options["admin_username"],
            email=options["admin_email"] or f"{options['admin_username']}@coopgestion.local",
            nombres=options["admin_nombres"],
            apellidos=options["admin_apellidos"],
            rol=rol_admin,
            password=options["admin_password"],
            sucursal=sucursal,
            debe_cambiar_password=True,
        )
        usuario.is_staff = True
        usuario.is_superuser = False
        usuario.save(update_fields=["is_staff", "actualizado_en"])
        self.stdout.write(self.style.SUCCESS(f"Administrador creado: {usuario.username}"))
        self.stdout.write(
            self.style.WARNING("Deberá cambiar la contraseña en el primer inicio de sesión.")
        )
