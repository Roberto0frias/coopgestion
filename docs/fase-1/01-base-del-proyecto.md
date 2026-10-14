# FASE 1 — Base del proyecto

| Campo | Valor |
|---|---|
| Documento | Entrega de la Fase 1: estructura, usuarios, roles, auditoría e interfaz base |
| Versión | 1.0 |
| Estado | Completada y verificada |
| Fecha | 14 de octubre de 2026 |

---

## 1. Qué se construyó

| Subfase | Entregable | Archivos principales |
|---|---|---|
| **1.1** | Estructura del repositorio, configuración por entornos y Docker | `config/settings/{base,dev,test,prod}.py`, `.env.example`, `docker-compose.yml`, `docker-compose.prod.yml`, `docker/Dockerfile`, `docker/nginx/coopgestion.conf` |
| **1.2** | Modelo de usuario personalizado, roles y permisos | `apps/usuarios/models.py`, `backends.py`, `permisos.py`, `services.py`, `forms.py`, `views.py` |
| **1.3** | Plantilla base con Tailwind + HTMX y navegación por rol | `templates/base.html`, `templates/inicio.html`, `assets/css/input.css`, `static/css/app.css`, `static/vendor/htmx.min.js` |
| **1.4** | Módulo de auditoría con cadena de hash | `apps/auditoria/{models,services,signals,context,middleware,registry,views}.py` |
| **1.5** | Pruebas y configuración de integración continua | `tests/`, `.github/workflows/ci.yml`, `pyproject.toml` |

Además se creó el módulo `apps/core` con los cimientos que necesitan todas las fases:
sucursales, monedas, feriados, parámetros del sistema, secuencias documentales
con bloqueo de fila e idempotencia de operaciones.

---

## 2. Cómo se ejecuta y se verifica

### Puesta en marcha desde cero

```powershell
# 1. Dependencias y base de datos local
uv sync --dev
powershell -ExecutionPolicy Bypass -File scripts\entorno\pg_start.ps1

# 2. Migraciones y datos iniciales (sucursal, moneda, parámetros, secuencias y roles)
uv run python manage.py migrate
uv run python manage.py sembrar_datos_iniciales `
    --admin-username roberto `
    --admin-email friasdelarosa0@gmail.com `
    --admin-password "Coopgestion2026!" `
    --admin-nombres Roberto --admin-apellidos "de la Rosa"

# 3. Hoja de estilos
powershell -ExecutionPolicy Bypass -File scripts\entorno\tailwind.ps1

# 4. Servidor de desarrollo
uv run python manage.py runserver
```

La aplicación queda en <http://127.0.0.1:8000/>.

> **Credenciales locales de demostración:** usuario `roberto`, contraseña
> `Coopgestion2026!`. El sistema obliga a cambiarla en el primer inicio de sesión. Es una
> credencial de desarrollo; cámbiela antes de usar datos reales.

### Verificación

```powershell
uv run pytest -q                              # 194 pruebas
uv run pytest --cov=apps --cov-report=term-missing
uv run ruff check .
uv run black --check .
uv run python manage.py check
uv run python manage.py verificar_cadena_auditoria
```

### Con Docker (equipo con Docker instalado)

```powershell
docker compose up --build
docker compose exec web python manage.py sembrar_datos_iniciales
```

---

## 3. Resultado de la verificación

| Comprobación | Resultado |
|---|---|
| Pruebas | **194 correctas** |
| Cobertura global de `apps` | **85.9 %** (umbral 80 %) |
| Cobertura de `apps/core/dinero.py` | **100 %** (umbral 90 % exigido a los módulos de cálculo) |
| `ruff check` | Sin hallazgos |
| `black --check` | Sin cambios pendientes |
| `manage.py check` | Sin problemas |
| Roles sembrados | 6 (ADMIN, CONTADOR, OFICIAL, CAJERO, COMITE, AUDITOR) |
| Permisos administrados | 65 |

---

## 4. Decisiones tomadas en esta fase

| # | Decisión | Motivo |
|---|---|---|
| F1-01 | Los permisos se resuelven con un **backend de autenticación propio** (`apps/usuarios/backends.py`) | El `ModelBackend` de Django lee `user_permissions` y grupos; anular `get_user_permissions()` en el modelo no afecta a `has_perm()`. Sin el backend, la matriz de roles no se aplicaba |
| F1-02 | **No se usan los grupos de Django** | La fuente de verdad de los permisos es el `Rol`, declarado en `permisos.py`. Duplicar en grupos permitiría que ambos divergieran |
| F1-03 | No se usa `raise_exception = True` en las vistas | Con esa opción, un usuario anónimo recibe 403 en lugar de ser enviado al login. El comportamiento correcto es: anónimo → login; autenticado sin permiso → 403 |
| F1-04 | El formulario de login **no llama a `authenticate()`** | Toda la validación pasa por `autenticar()`, que aplica intentos fallidos, bloqueo y registro. Llamar al método padre de `AuthenticationForm` saltaba la política completa |
| F1-05 | Los permisos se aplican con `python manage.py sembrar_roles`, comando **idempotente** | Cada fase nueva añade permisos a la matriz y basta con volver a ejecutarlo |
| F1-06 | La cadena de auditoría se serializa con `pg_advisory_xact_lock` | Con dos peticiones simultáneas, ambas podrían calcular el mismo hash anterior y romper la cadena |
| F1-07 | Los campos `password` y `actualizado_en` se excluyen de la auditoría | El primero por seguridad; el segundo cambia en cada guardado y generaría registros sin cambios reales |
| F1-08 | Sesión con expiración **por inactividad** (30 min) | Es la política acordada; se implementa con `SESSION_SAVE_EVERY_REQUEST` |
| F1-09 | `ATOMIC_REQUESTS = False` | La atomicidad la controla la capa de servicios, que es donde están las reglas de negocio |
| F1-10 | Tailwind con el **binario independiente** (v4), no con Node | El repositorio no necesita `node_modules` ni una cadena de compilación de JavaScript |
| F1-11 | HTMX se versiona dentro del repositorio | Evita dependencias externas en producción y permite trabajar sin conexión |
| F1-12 | **Rol COMITE creado** (decisión P-13) | El flujo de aprobación de créditos exige que quien aprueba sea distinto de quien solicita |
| F1-13 | **La tasa de interés de ahorro no se siembra** (decisión P-04) | El cálculo de intereses debe fallar con un mensaje claro antes que inventar una tasa |

---

## 5. Defectos encontrados y corregidos durante la fase

Todos aparecieron al ejecutar las pruebas, no por inspección teórica.

| # | Defecto | Impacto si no se corrige |
|---|---|---|
| H-09 | El manejador de registro de desarrollo fallaba en cada mensaje porque `logs/` no existía | El registro quedaba inutilizado y llenaba la salida de errores |
| H-10 | `has_perm()` ignoraba por completo el rol del usuario | **La matriz de permisos no se aplicaba**: cualquier usuario habría tenido los permisos del backend por omisión, no los de su rol |
| H-11 | `raise_exception = True` devolvía 403 al usuario anónimo en lugar de enviarlo al login | Usuarios sin sesión verían "Prohibido" en lugar de la pantalla de acceso |
| H-12 | El formulario de login llamaba a `authenticate()` de Django | **La política de bloqueo por intentos fallidos era inoperante** desde la interfaz |
| H-13 | `verificar_cadena(limite=N)` marcaba la cadena como rota al verificar un tramo | Un reporte de integridad daría falsos positivos en producción |
| H-14 | Faltaban las plantillas de parámetros (`core/parametros_lista.html`) | Error 500 al abrir la sección |

---

## 6. Pendientes que arrastra la Fase 1

| Pendiente | Fase en que se resuelve |
|---|---|
| Validar el catálogo de cuentas y las políticas contables con el contador (P-03) | Fase 2 |
| Definir la tasa de interés de ahorro (P-04) | Antes de la Fase 4 |
| Tabla de provisiones por antigüedad (P-05) | Fase 2 y 5 |
| Tope legal de la mora (P-10) | Antes de la Fase 5 |
| Validar el algoritmo del dígito verificador de la cédula con cédulas reales (P-18) | Fase 3 |
| RNC y autorización de la DGII para emitir NCF (P-01, P-02) | Antes de la Fase 6 |
| 2FA (autenticación en dos pasos) | Fase 7 |
| WeasyPrint para los PDF | Fase 6 |

---

## 7. Cómo entra cada fase siguiente en esta base

- **Fase 2 (contabilidad)**: añade `apps/contabilidad` y sus modelos; registra los nuevos
  modelos en `apps/auditoria/registry.py` y añade sus permisos a la matriz.
- **Fases 3 a 5 (socios, ahorros, préstamos)**: cada módulo declara sus permisos, usa
  `siguiente_numero()` para sus comprobantes, `ejecutar_una_vez()` para evitar el doble
  posteo y `contabilizar()` para generar asientos.
- **Las vistas nuevas** deben seguir el patrón establecido: delgadas, con permisos
  declarados, y toda la lógica en `services.py`.
