#!/usr/bin/env python
"""Utilidad de línea de comandos de Django para COOPGESTION."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    """Ejecuta una tarea administrativa de Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - error de instalación
        raise ImportError(
            "No se pudo importar Django. ¿Está activado el entorno virtual?\n"
            "Ejecute: uv sync --dev"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
