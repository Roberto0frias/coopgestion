"""Comando que aplica la matriz de roles y permisos sobre la base de datos.

Es idempotente: se puede volver a ejecutar cada vez que un módulo declare permisos
nuevos, y siempre deja la base de datos igual a lo declarado en
``apps/usuarios/permisos.py``.

Uso:
    python manage.py sembrar_roles
    python manage.py sembrar_roles --solo-verificar
"""

from __future__ import annotations

from apps.usuarios.models import Rol
from apps.usuarios.permisos import (
    MATRIZ_PERMISOS,
    PERMISOS_PROHIBIDOS_SOLO_LECTURA,
    ROLES,
)
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction


class Command(BaseCommand):
    help = "Crea o actualiza los roles del sistema y sus permisos según la matriz declarada."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--solo-verificar",
            action="store_true",
            help="No modifica nada; solo informa qué cambiaría.",
        )

    def handle(self, *args, **options) -> None:
        solo_verificar: bool = options["solo_verificar"]
        permisos_disponibles = {
            f"{p.content_type.app_label}.{p.codename}": p
            for p in Permission.objects.select_related("content_type")
        }
        self.stdout.write(f"Permisos declarados en la base de datos: {len(permisos_disponibles)}")

        for codigo, datos in ROLES.items():
            with transaction.atomic():
                self._procesar_rol(codigo, datos, permisos_disponibles, solo_verificar)

    # ------------------------------------------------------------------ #
    def _procesar_rol(
        self,
        codigo: str,
        datos: dict,
        permisos_disponibles: dict[str, Permission],
        solo_verificar: bool,
    ) -> None:
        rol = Rol.objects.filter(codigo=codigo).first()
        creado = rol is None
        if creado:
            if solo_verificar:
                self.stdout.write(self.style.WARNING(f"[crearía] rol {codigo} · {datos['nombre']}"))
                return
            rol = Rol.objects.create(codigo=codigo)

        assert rol is not None
        rol.nombre = datos["nombre"]
        rol.descripcion = datos["descripcion"]
        rol.es_solo_lectura = datos["es_solo_lectura"]
        rol.orden = datos["orden"]
        rol.activo = True

        codigos_deseados = MATRIZ_PERMISOS.get(codigo, set())
        if "*" in codigos_deseados:
            seleccionados = list(permisos_disponibles.values())
        else:
            seleccionados = [
                permiso
                for etiqueta, permiso in permisos_disponibles.items()
                if etiqueta in codigos_deseados
            ]
            faltantes = codigos_deseados - {
                f"{p.content_type.app_label}.{p.codename}" for p in seleccionados
            }
            for etiqueta in sorted(faltantes):
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{codigo}] el permiso «{etiqueta}» aún no existe en la base de datos"
                    )
                )

        if rol.es_solo_lectura:
            seleccionados = [
                permiso for permiso in seleccionados if not self._es_permiso_de_escritura(permiso)
            ]

        if solo_verificar:
            self.stdout.write(f"[revisaría] {codigo} · {len(seleccionados)} permiso(s)")
            return

        rol.save()
        rol.permisos.set(seleccionados)
        accion = "creado" if creado else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Rol {codigo} {accion} · {len(seleccionados)} permiso(s) · "
                f"{'solo lectura' if rol.es_solo_lectura else 'operativo'}"
            )
        )

    @staticmethod
    def _es_permiso_de_escritura(permiso: Permission) -> bool:
        """Indica si un permiso permite modificar datos."""
        etiqueta = f"{permiso.content_type.app_label}.{permiso.codename}"
        if etiqueta in PERMISOS_PROHIBIDOS_SOLO_LECTURA:
            return True
        return permiso.codename.startswith(("add_", "change_", "delete_"))
