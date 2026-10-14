# COOPGESTION — Entorno de desarrollo verificado

| Campo | Valor |
|---|---|
| Documento | Entorno preparado, hallazgos corregidos y evidencia de ejecución |
| Fecha | 14 de octubre de 2026 |
| Fase | Preparación previa a la Fase 1 |
| Estado | **Verificado y operativo** |

---

## 1. Resumen

El entorno de desarrollo está operativo en esta máquina **sin permisos de administrador** y sin
tocar la instalación previa de PostgreSQL 18 que ya existía. Se logró:

| Verificación | Resultado |
|---|---|
| PostgreSQL 16 exigido por el stack | **16.15** en ejecución en `127.0.0.1:5433` |
| Suite de pruebas | **59 pruebas, 59 correctas** en 1.2 s |
| Cobertura de `apps/core` | **100 %** (umbral exigido: 90 %) |
| `ruff check` | Sin hallazgos |
| `black --check` | Sin cambios pendientes |
| Git | Repositorio inicializado en la rama `main` |
| NCF | **Desactivado** por decisión del responsable |

---

## 2. Componentes instalados

| Componente | Versión | Ubicación |
|---|---|---|
| Git for Windows | 2.55.0.windows.5 | `C:\Program Files\Git\cmd\git.exe` |
| uv | 0.13.1 | `C:\Users\frias\.local\bin\uv.exe` |
| CPython (gestionado por uv) | 3.12.15 | `coopgestion\.venv` |
| PostgreSQL | 16.15 (binarios oficiales EDB) | `C:\Users\frias\.coopgestion\pgsql` |

### Dependencias Python principales

| Paquete | Versión |
|---|---|
| Django | 5.2.18 |
| psycopg | 3.3.6 |
| django-environ | 0.14.0 |
| django-q2 | 1.11.1 |
| argon2-cffi | 25.1.0 |
| openpyxl | 3.1.5 |
| pytest | 9.1.1 |
| pytest-django | 4.14.0 |
| pytest-cov | 7.1.0 |
| Hypothesis | 6.169.1 |
| factory-boy | 3.3.3 |
| ruff | 0.17.0 |
| black | 26.10.1 |

> `WeasyPrint` no se instala todavía: requiere GTK en Windows y solo se necesita para la
> generación de PDF (Fase 6), que se ejecutará dentro de Docker.

### Procedencia de los binarios de PostgreSQL

| Dato | Valor |
|---|---|
| Origen | `https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip` |
| Tamaño | 317 MB |
| SHA-256 | `25E6FCDFB8CAEC38691BF461125E7564508760666F7B8E5DC6A5F0818F58F81E` |
| Extraído en | `C:\Users\frias\.coopgestion\pgsql` (834 MB) |

> Se eligió 16.15 porque es la última versión 16.x publicada: las versiones 16.16 y superiores
> devuelven 403 en el servidor de descargas.

---

## 3. Configuración del clúster

| Parámetro | Valor |
|---|---|
| Directorio de datos | `C:\Users\frias\.coopgestion\pgdata` |
| Host y puerto | `127.0.0.1:5433` |
| Codificación | UTF8 |
| Configuración regional | `C` |
| Zona horaria | `America/Santo_Domingo` |
| Registro del servidor | `C:\Users\frias\.coopgestion\pgdata\log\postgresql-AAAA-MM-DD.log` (recolector propio de PostgreSQL, rotación diaria) |

**El puerto 5433 y la instalación previa de PostgreSQL 18.6 en el puerto 5432 no se tocan.** Esta
máquina tenía un servicio `postgresql-x64-18` en ejecución que se dejó intacto.

### Dos roles, por principio de menor privilegio

| Rol | Privilegios | Uso |
|---|---|---|
| `postgres` | Superusuario | Solo administración: crear roles y bases de datos |
| `coopgestion` | `NOSUPERUSER`, `NOCREATEROLE`, `CREATEDB` | Rol de la aplicación y de las pruebas |

`CREATEDB` se concede **solo en desarrollo**, porque pytest-django lo necesita para crear la base
de datos de pruebas. En producción el rol de la aplicación no tendrá ese privilegio.

> Las contraseñas de desarrollo (`coopgestion_admin`, `coopgestion_dev`) están en
> `scripts/entorno/comun.ps1` y son **exclusivamente locales**. En producción los secretos van en
> variables de entorno, nunca en el repositorio.

---

## 4. Cómo se usa

Los scripts funcionan igual con **Windows PowerShell 5.1** (`powershell`) y con **PowerShell 7**
(`pwsh`). Se recomienda `pwsh`; ambos se verificaron.

> **Aviso para quien edite los scripts:** deben guardarse en **UTF-8 con BOM**. Si un editor los
> guarda sin BOM, Windows PowerShell 5.1 los leerá como ANSI y una «Ó» o una «Ñ» romperá el
> analizador sintáctico (hallazgo H-07).

```powershell
# Estado del entorno (PostgreSQL, Python, repositorio)
powershell -ExecutionPolicy Bypass -File scripts\entorno\estado.ps1

# Arrancar / detener PostgreSQL
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_start.ps1
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_stop.ps1

# Inicialización completa desde cero (extrae, crea el clúster, roles y base de datos)
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_init.ps1

# Dependencias del proyecto
uv sync --dev

# Pruebas
uv run pytest -v
uv run pytest --cov=apps --cov-report=term-missing

# Calidad de código
uv run ruff check .
uv run black --check .
```

### Evidencia de la última ejecución

```
collected 59 items
tests\test_dinero.py ..........................................  [82%]
tests\test_entorno_postgres.py .........                          [100%]
59 passed in 1.20s

Name                  Stmts   Miss Branch BrPart  Cover
apps\core\dinero.py      93      0     42      0   100%
Required test coverage of 90.0% reached. Total coverage: 100.00%
```

---

## 5. Hallazgos corregidos durante la preparación

Estos son defectos reales que aparecieron al ejecutar las pruebas, no hipótesis:

| # | Hallazgo | Impacto si no se corrige | Corrección aplicada |
|---|---|---|---|
| H-01 | `initdb` crea al usuario bootstrap como **superusuario**, y la aplicación se conectaba con ese rol | La aplicación operaría con privilegios totales: podría borrar tablas y saltarse cualquier control | Dos roles separados: `postgres` (administrador) y `coopgestion` (aplicación, `NOSUPERUSER`). Prueba automática que lo verifica |
| H-02 | `repartir()` redondeaba la base con `HALF_UP` | Con totales pequeños (**0.02 en 4 partes**) producía una **parte negativa**: cuotas con interés negativo | Base calculada con `ROUND_FLOOR`; el residuo queda en la última cuota y ninguna parte puede ser negativa |
| H-03 | Al repartir el total de la cuota y restar el capital, el interés de la última cuota podía salir negativo | Cuota con interés negativo y descuadre en la tabla de amortización | Capital e interés se reparten por separado; el residuo de cada uno queda en la última cuota |
| H-04 | `Start-Process -PassThru` + `WaitForExit()` devuelve `ExitCode` vacío en Windows PowerShell 5.1 | El script abortaba tras arrancar PostgreSQL, dejando el rol y la base sin crear | Arranque directo con `postgres.exe` y sondeo con `pg_isready` |
| H-05 | Un trabajo en segundo plano que arrancaba PostgreSQL quedaba abierto indefinidamente (el servidor heredaba la tubería de salida), y **cancelarlo mataba el servidor** | Imposible automatizar el arranque; riesgo de tumbar la base al cancelar un trabajo | Arranque desacoplado con `Start-Process` y salidas redirigidas a archivo |
| H-06 | La fixture `autouse` de `conftest.py` obligaba a tener base de datos para correr **cualquier** prueba | Las pruebas de cálculo puro fallarían sin PostgreSQL, ocultando errores reales | La creación del esquema se movió a la fixture `conexion`; las pruebas de cálculo no dependen de la base |
| H-07 | Los scripts `.ps1` guardados en UTF-8 **sin BOM** se leen como ANSI en Windows PowerShell 5.1: la «Ó» de "EJECUCIÓN" se convierte en una comilla tipográfica | `estado.ps1` no se podía ejecutar: error de sintaxis por cadena sin terminar | Todos los scripts se guardan en **UTF-8 con BOM** y se verificó su ejecución bajo PowerShell 5.1 |
| H-08 | `postgres.exe` lanzado con `Start-Process` heredaba la tubería de salida del shell | Cualquier comando que arrancara el servidor quedaba colgado indefinidamente (y cancelarlo mataba la base) | Arranque por **WMI (`Win32_Process.Create`)**: proceso totalmente desacoplado, mismo usuario, listo en 0,5 s, sin retener ninguna tubería |

---

## 6. Archivos creados en esta preparación

| Ruta | Contenido |
|---|---|
| [`pyproject.toml`](../../pyproject.toml) | Dependencias, pytest, cobertura, ruff y black |
| [`apps/core/dinero.py`](../../apps/core/dinero.py) | Aritmética monetaria: única puerta de redondeo del sistema |
| [`tests/test_dinero.py`](../../tests/test_dinero.py) | 50 pruebas de cálculo, incluidas dos basadas en propiedades |
| [`tests/test_entorno_postgres.py`](../../tests/test_entorno_postgres.py) | 9 pruebas de infraestructura: versión, precisión `NUMERIC`, bloqueo de filas, atomicidad y privilegios |
| [`tests/conftest.py`](../../tests/conftest.py) | Conexión a PostgreSQL y parámetros por entorno |
| [`scripts/entorno/comun.ps1`](../../scripts/entorno/comun.ps1) | Variables y funciones de gestión del clúster |
| [`scripts/entorno/pg_init.ps1`](../../scripts/entorno/pg_init.ps1) | Inicialización completa desde cero |
| [`scripts/entorno/pg_start.ps1`](../../scripts/entorno/pg_start.ps1) | Arranque |
| [`scripts/entorno/pg_stop.ps1`](../../scripts/entorno/pg_stop.ps1) | Parada ordenada |
| [`scripts/entorno/estado.ps1`](../../scripts/entorno/estado.ps1) | Diagnóstico del entorno |
| [`.gitignore`](../../.gitignore) · [`.gitattributes`](../../.gitattributes) · [`.python-version`](../../.python-version) | Configuración del repositorio |

---

## 7. Reglas financieras ya implementadas y probadas

| Regla | Decisión | Estado |
|---|---|---|
| Interés flat sobre capital inicial | D-01 | Implementado y probado |
| Equivalencia de frecuencias (1 mes = 4 semanas) | D-02 | Implementado y probado |
| Mora del 5 % acumulable por período, con tope opcional | D-03 | Implementado y probado |
| Interés de ahorro por saldo promedio diario, base 360 | D-04 | Implementado y probado |
| Redondeo `HALF_UP` a 2 decimales | D-07 | Implementado y probado |
| Residuo de centavos en la última cuota | D-07 | Implementado y probado |
| Ninguna cuota con interés o capital negativo | Invariante | Verificado con pruebas basadas en propiedades |

---

## 8. Pendientes de esta preparación

| Pendiente | Motivo |
|---|---|
| Configurar la identidad de Git (`user.name` y `user.email`) | Sin ella no se puede crear el commit de la Fase 0 |
| Crear la rama `develop` | Requiere al menos un commit en `main` |
| `docker-compose.yml` | Se entrega en la Fase 1, junto con la estructura del repositorio |
| Activar `pytest-django` | Requiere `config/settings`, que se crea en la Fase 1 (hoy pytest corre con `-p no:django`) |
| WeasyPrint | Se instala en la Fase 6, para los PDF |
