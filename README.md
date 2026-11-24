# COOPGESTION · Sistema interno de gestión

Sistema web interno (solo personal) para la Cooperativa de Ahorro y Crédito **COOPGESTION**:
socios, ahorros, préstamos, contabilidad y reportes, con integridad financiera verificable.

> **Estado:** Fase 0 completada; Fases 1 y 2 en desarrollo. Están disponibles el acceso interno,
> el panel, los expedientes y la admisión de socios, y el libro diario con confirmación de
> partida doble y corrección mediante reverso aprobado. Ahorros tiene configuración inicial; préstamos aún no están habilitados.

## Stack

Python 3.12 · Django 5 · PostgreSQL 16 · HTMX · pytest · ruff · black · uv · Docker.

## Entorno de desarrollo (Windows, sin permisos de administrador)

El proyecto usa un **PostgreSQL 16.15 portable en espacio de usuario** (puerto `5433`),
independiente de cualquier instalación previa en la máquina. Estado verificado y detalle completo
en [`docs/fase-0/05-entorno-verificado.md`](docs/fase-0/05-entorno-verificado.md).

```powershell
# 0. Preparar configuración local
Copy-Item .env.example .env
# Configura DJANGO_SECRET_KEY con una clave aleatoria antes de usar el sistema.

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

### Ejecutar la aplicación

Con PostgreSQL iniciado y dependencias instaladas:

```powershell
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. El panel requiere una cuenta activa. Las cuentas de usuarios
internos se administran desde `/admin/`; el rol Auditor dispone de acceso de solo lectura a la
bitácora. Los intentos de acceso fallidos se bloquean después de cinco intentos durante quince
minutos, por defecto. Se puede cambiar ese límite con `INTENTOS_LOGIN_MAXIMOS` y
`MINUTOS_BLOQUEO_LOGIN`. Si el administrador marca una contraseña como temporal, el usuario debe
cambiarla antes de usar el resto de la aplicación.

### Docker Compose local

Para un entorno local aislado, configura `.env` y ejecuta `docker compose up --build`. Compose
publica el sitio solo en `127.0.0.1`, aplica migraciones y recopila archivos estáticos antes de
iniciar Gunicorn. Este Compose es para desarrollo local; antes de desplegar en un VPS se debe
configurar un proxy HTTPS y reemplazar todos los secretos y contraseñas.

La cadena de auditoría se comprueba con `uv run python manage.py verificar_cadena_auditoria`.
Los eventos no se pueden editar ni borrar desde Django; PostgreSQL también instala un trigger que
rechaza `UPDATE` y `DELETE`.

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

## Estado del desarrollo

- **Fase 0:** arquitectura, reglas financieras y entorno local documentados.
- **Fase 1 en curso:** proyecto Django, configuración por entorno, usuario con roles, inicio de
  sesión, bloqueo temporal, panel interno, auditoría encadenada y expedientes de socios con
  separación entre registro y admisión.
- **Contabilidad en curso:** catálogo editable, períodos contables, asientos en borrador y
  confirmación con secuencia mensual, inmutabilidad, reversos con aprobación independiente y validación de partida doble. El catálogo
  sigue pendiente de revisión por un contador (P-03); no se precargan cuentas sin esa aprobación.
- **Ahorros en preparación:** productos sujetos a tasa aprobada, cuentas solo para socios admitidos y pantalla informativa de movimientos. No hay depósitos ni retiros hasta integrar Caja y catálogo aprobado.
- **Pendiente:** completar documentos del expediente, préstamos, caja, reportes, flujos operativos, despliegue y procedimientos de respaldo.
