#!/bin/sh
# Punto de entrada del contenedor: espera la base de datos, migra y recoge estáticos.
set -e

echo "[entrada] Iniciando COOPGESTION ..."

if [ -n "$DATABASE_URL" ]; then
    echo "[entrada] Esperando a PostgreSQL ..."
    python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ.get("DATABASE_URL", "")
intentos = 30
for intento in range(1, intentos + 1):
    try:
        with psycopg.connect(url, connect_timeout=3):
            print(f"[entrada] PostgreSQL disponible (intento {intento}).")
            sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[entrada] Intento {intento}/{intentos}: {exc}")
        time.sleep(2)
print("[entrada] ERROR: PostgreSQL no respondió a tiempo.", file=sys.stderr)
sys.exit(1)
PY
fi

echo "[entrada] Aplicando migraciones ..."
python manage.py migrate --noinput

echo "[entrada] Recogiendo archivos estáticos ..."
python manage.py collectstatic --noinput --clear > /dev/null

echo "[entrada] Listo. Ejecutando: $*"
exec "$@"
