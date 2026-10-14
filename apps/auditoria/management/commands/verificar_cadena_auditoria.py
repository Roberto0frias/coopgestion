"""Comando para verificar la integridad de la bitácora de auditoría.

Uso:
    python manage.py verificar_cadena_auditoria
    python manage.py verificar_cadena_auditoria --limite 5000

Devuelve código de salida 1 si la cadena está rota, de modo que sirva en un monitoreo
automático o en una tarea programada.
"""

from __future__ import annotations

from apps.auditoria.models import RegistroAuditoria
from apps.auditoria.services import verificar_cadena
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Verifica que la cadena de hash de la bitácora de auditoría esté intacta."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--limite",
            type=int,
            default=None,
            help="Cantidad máxima de registros recientes a verificar (por omisión, todos).",
        )

    def handle(self, *args, **options) -> None:
        limite = options["limite"]
        total = RegistroAuditoria.objects.count()
        self.stdout.write(f"Registros en la bitácora: {total}")

        resultado = verificar_cadena(limite=limite)

        if resultado["integridad"]:
            self.stdout.write(self.style.SUCCESS(f"CADENA ÍNTEGRA · {resultado['detalle']}"))
            return

        self.stdout.write(self.style.ERROR("CADENA ALTERADA"))
        self.stdout.write(f"  Revisados      : {resultado['revisados']}")
        self.stdout.write(f"  Primer error en: registro {resultado['primer_error_id']}")
        self.stdout.write(f"  Detalle        : {resultado['detalle']}")
        raise SystemExit(1)
