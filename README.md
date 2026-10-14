# COOPGESTION · Sistema interno de gestión

Sistema web interno (solo personal) para la Cooperativa de Ahorro y Crédito **COOPGESTION**:
socios, ahorros, préstamos, contabilidad y reportes, con integridad financiera verificable.

> **Estado:** Fase 0 completada (diseño). Fase 1 en preparación.
> La documentación de diseño está en [`docs/fase-0/`](docs/fase-0/).

## Stack

Python 3.12 · Django 5 · PostgreSQL 16 · HTMX + Tailwind CSS · pytest · ruff · black · uv · Docker.

## Entorno de desarrollo (Windows, sin permisos de administrador)

El proyecto usa un **PostgreSQL 16.15 portable en espacio de usuario** (puerto `5433`),
independiente de cualquier instalación previa en la máquina. Estado verificado y detalle completo
en [`docs/fase-0/05-entorno-verificado.md`](docs/fase-0/05-entorno-verificado.md).

```powershell
# 0. Estado del entorno
powershell -ExecutionPolicy Bypass -File scripts\entorno\estado.ps1

# 1. Dependencias del proyecto
uv sync --dev

# 2. Arrancar PostgreSQL local (lo inicializa si es la primera vez)
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_start.ps1

# 3. Ejecutar las pruebas
uv run pytest -v

# 4. Calidad de código
uv run ruff check .
uv run black --check .

# 5. Detener PostgreSQL local
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_stop.ps1
```

### Parámetros de conexión de desarrollo

| Parámetro | Valor |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `5433` |
| Base de datos | `coopgestion` |
| Usuario de la aplicación | `coopgestion` (`NOSUPERUSER`) |
| Contraseña de la aplicación | `coopgestion_dev` (solo desarrollo local) |
| Usuario administrador del clúster | `postgres` (solo para crear roles y bases) |
| Codificación | UTF8 |
| Zona horaria | `America/Santo_Domingo` |

## Reglas financieras innegociables

1. Todo monto usa `Decimal` / `NUMERIC(18,2)`. **Prohibido `float`.**
2. Partida doble: `Σ débitos = Σ créditos` verificado en la capa de servicios **y** en la base de datos.
3. Los saldos se derivan de los asientos; nunca se editan a mano.
4. Los registros confirmados son inmutables: se corrigen con asiento de reverso.
5. Toda operación financiera corre en `transaction.atomic` con `select_for_update()` donde haya concurrencia.
6. La lógica de negocio vive en `services.py`, nunca en vistas ni plantillas.

## Configuración pendiente

- `EMISION_NCF_ACTIVA = false`: no se emite ningún comprobante fiscal hasta que existan RNC y
  autorización de la DGII (ver `docs/fase-0/00-levantamiento-y-decisiones.md`, punto P-01).
