from django.core.management.base import BaseCommand, CommandError

from apps.auditoria.services import verificar_cadena


class Command(BaseCommand):
    help = "Verifica la integridad de la cadena de auditoría."

    def handle(self, *args, **options) -> None:
        del args, options
        valida, evento_id = verificar_cadena()
        if not valida:
            detalle = f" en el evento {evento_id}" if evento_id else " en el hash final"
            raise CommandError(f"La cadena de auditoría no es válida{detalle}.")
        self.stdout.write(self.style.SUCCESS("Cadena de auditoría íntegra."))
