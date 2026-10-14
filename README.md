# COOPGESTION · Sistema interno de gestión

Sistema web interno (solo personal) para la Cooperativa de Ahorro y Crédito **COOPGESTION**:
socios, ahorros, préstamos, contabilidad y reportes, con integridad financiera verificable.

| Fase | Estado |
|---|---|
| **Fase 0** — Levantamiento y diseño | ✅ Cerrada · [documentación](docs/fase-0/) |
| **Fase 1** — Base del proyecto | ✅ Cerrada · [documentación](docs/fase-1/01-base-del-proyecto.md) |
| Fase 2 — Núcleo contable | ⏸️ Pendiente de aprobación |

## Stack

Python 3.12 · Django 5.2 · PostgreSQL 16 · HTMX + Tailwind CSS · pytest · ruff · black · uv · Docker.

## Puesta en marcha (desarrollo en Windows, sin permisos de administrador)

El proyecto usa un **PostgreSQL 16.15 portable en el perfil del usuario** (puerto `5433`),
independiente de cualquier instalación previa. Detalle en
[docs/fase-0/05-entorno-verificado.md](docs/fase-0/05-entorno-verificado.md).

```powershell
# 0. Estado del entorno (PostgreSQL, Python, repositorio)
powershell -ExecutionPolicy Bypass -File scripts\entorno\estado.ps1

# 1. Dependencias del proyecto
uv sync --dev

# 2. Arrancar PostgreSQL local (lo inicializa la primera vez)
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_start.ps1

# 3. Migraciones y datos iniciales (sucursal, moneda, parámetros, secuencias y roles)
uv run python manage.py migrate
uv run python manage.py sembrar_datos_iniciales `
    --admin-username roberto `
    --admin-email friasdelarosa0@gmail.com `
    --admin-password "Coopgestion2026!" `
    --admin-nombres Roberto --admin-apellidos "de la Rosa"

# 4. Hoja de estilos (Tailwind CSS v4, sin Node)
powershell -ExecutionPolicy Bypass -File scripts\entorno\tailwind.ps1

# 5. Servidor de desarrollo
uv run python manage.py runserver
```

La aplicación queda en <http://127.0.0.1:8000/>.

> **Credenciales locales de demostración:** usuario `roberto`, contraseña
> `Coopgestion2026!`. El sistema **obliga a cambiarla** en el primer inicio de sesión.
> Es una credencial de desarrollo: cámbiela antes de usar datos reales.

## Comandos habituales

```powershell
uv run pytest -q                                    # 194 pruebas
uv run pytest --cov=apps --cov-report=term-missing  # cobertura
uv run ruff check .                                 # estilo
uv run black .                                      # formato
uv run python manage.py check                       # revisión del proyecto
uv run python manage.py sembrar_roles               # reaplicar la matriz de permisos
uv run python manage.py verificar_cadena_auditoria  # integridad de la bitácora
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_stop.ps1
```

## Con Docker

```powershell
docker compose up --build
docker compose exec web python manage.py sembrar_datos_iniciales
```

## Estructura

```
coopgestion/
├── config/settings/     # base · dev · test · prod
├── apps/
│   ├── core/            # sucursales, parámetros, secuencias, idempotencia y dinero
│   ├── usuarios/        # usuario personalizado, roles, permisos y autenticación
│   └── auditoria/       # bitácora inmutable con cadena de hash
├── templates/           # plantillas Django + HTMX + Tailwind
├── assets/css/          # fuente de Tailwind (se compila a static/css/app.css)
├── tests/               # 194 pruebas: cálculo, seguridad, auditoría y vistas
├── scripts/entorno/     # PostgreSQL portable y compilación de estilos
├── docker/              # Dockerfile, entrypoint y Nginx
└── docs/                # fase-0 (diseño) y fase-1 (base del proyecto)
```

## Reglas financieras innegociables

1. Todo monto usa `Decimal` / `NUMERIC(18,2)`. **Prohibido `float`.**
2. Partida doble: `Σ débitos = Σ créditos` verificado en los servicios y en la base de datos.
3. Los saldos se derivan de los asientos; nunca se editan a mano.
4. Los registros confirmados son inmutables: se corrigen con asiento de reverso.
5. Toda operación financiera corre en `transaction.atomic` con `select_for_update()` donde
   haya concurrencia, y es idempotente frente a dobles clics.
6. La lógica de negocio vive en `services.py`, nunca en vistas ni plantillas.
7. Los permisos provienen del **rol** del usuario, no de los grupos de Django.

## Configuración pendiente

- `EMISION_NCF_ACTIVA = false`: no se emite ningún comprobante fiscal hasta que existan RNC
  y autorización de la DGII (decisión D-08).
- La **tasa de interés de ahorro** no está definida a propósito (decisión D-13). Debe
  fijarse antes de la Fase 4.
