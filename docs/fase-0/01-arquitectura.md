# COOPGESTION — Arquitectura del sistema

| Campo | Valor |
|---|---|
| Documento | Arquitectura, estructura de aplicaciones y decisiones técnicas |
| Versión | 1.0 |
| Fase | 0.2 |
| Estado | Propuesta para aprobación |

---

## 1. Principios rectores

1. **La integridad financiera manda sobre la comodidad.** Ninguna funcionalidad se entrega si puede producir un descuadre.
2. **Los saldos se derivan, no se editan.** Todo saldo es la suma de hechos contables confirmados. No existe ninguna pantalla que permita "corregir" un saldo a mano.
3. **Nada se borra.** Un movimiento confirmado es inmutable; se corrige con asiento de reverso y queda la huella de quién, qué, cuándo y por qué.
4. **Una sola vía de escritura.** Todo cambio de estado financiero pasa por un servicio (`services.py`) dentro de una transacción atómica. Vistas y plantillas no calculan dinero.
5. **Trazo completo.** Cada operación de negocio genera un comprobante, un asiento contable y uno o más registros de auditoría, enlazados entre sí.
6. **Lo configurable se configura; lo legal se valida.** Tasas, umbrales, porcentajes de mora y de provisión viven en parámetros. Ninguna alícuota legal se codifica sin confirmación escrita.

---

## 2. Stack técnico

| Capa | Tecnología | Versión | Notas |
|---|---|---|---|
| Lenguaje | Python | 3.12+ | Tipado con type hints; `Decimal` obligatorio en dinero |
| Framework | Django | 5.x | Monolito modular con apps por dominio |
| Base de datos | PostgreSQL | 16 | `NUMERIC`, transacciones, bloqueo de filas, JSONB |
| Interfaz | Django Templates + HTMX | HTMX 2.x | Sin SPA; renderizado en servidor |
| Estilos | Tailwind CSS | 3.x/4.x | Compilado con CLI standalone; sin CDN en producción |
| Dependencias | uv | última | `pyproject.toml` + `uv.lock` |
| Configuración | django-environ | última | Todo secreto por variables de entorno |
| Pruebas | pytest + pytest-django | últimas | `factory_boy` + `hypothesis` |
| Calidad | ruff + black | últimas | Reglas estrictas, formato automático |
| Tareas programadas | django-q2 | última | Broker ORM (PostgreSQL); evita Redis a esta escala |
| PDF | WeasyPrint | última | HTML → PDF con membrete |
| Excel | openpyxl / XlsxWriter | últimas | Exportaciones |
| Servidor | Gunicorn + Nginx | últimas | HTTPS, archivos estáticos, límites |
| Contenedores | Docker + Docker Compose | últimas | Producción; desarrollo nativo o Compose |
| Respaldos | pg_dump + age (cifrado) | — | Diario, cifrado, con prueba de restauración |

---

## 3. Estructura del repositorio

```
coopgestion/
├── config/
│   ├── settings/
│   │   ├── base.py            # común a todos los entornos
│   │   ├── dev.py             # DEBUG, PostgreSQL local, django-q2 síncrono
│   │   ├── test.py            # base de datos de pruebas, hasher rápido
│   │   └── prod.py            # HTTPS, HSTS, cookies seguras, logs
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/                  # base abstracta, dinero, secuencias, parámetros, sucursal, moneda
│   ├── usuarios/              # Usuario, Rol, permisos, aprobaciones, bloqueo por intentos
│   ├── auditoria/             # bitácora inmutable encadenada por hash
│   ├── contabilidad/          # cuentas, períodos, asientos, líneas, plantillas, saldos
│   ├── socios/                # socios, beneficiarios, referencias, documentos, aportaciones
│   ├── ahorros/               # productos, cuentas, movimientos, intereses, saldos diarios
│   ├── prestamos/             # productos, solicitudes, préstamos, cuotas, pagos, mora
│   ├── caja/                  # cajas, turnos, arqueos, movimientos, caja chica
│   ├── documentos/            # comprobantes, secuencias documentales, NCF
│   └── reportes/              # generación PDF/Excel y registro de reportes emitidos
├── templates/
│   ├── base.html              # Tailwind + HTMX + navegación por rol
│   ├── components/            # tablas, formularios, modales HTMX
│   └── <app>/…
├── static/                    # fuente Tailwind y salida compilada
├── tests/
│   ├── unit/                  # cálculo puro: intereses, amortización, mora, redondeo
│   ├── integration/           # servicios con base de datos y asientos
│   ├── concurrency/           # TransactionTestCase + hilos
│   └── e2e/                   # flujos completos por rol
├── docs/
│   ├── fase-0/                # este directorio
│   ├── manuales/              # manual por rol (Fase 7)
│   └── despliegue/            # guía de despliegue y respaldo (Fase 7)
├── docker/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── nginx/coopgestion.conf
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   └── verificar_cuadre.py    # comando de cuadre diario
├── pyproject.toml
├── uv.lock
├── docker-compose.yml         # desarrollo
├── docker-compose.prod.yml    # producción
├── .env.example
├── .github/workflows/ci.yml
├── Makefile
└── README.md
```

---

## 4. Capas y reglas de dependencia

```
Plantillas (HTML/HTMX)
      ▲
    Vistas  (delgadas: validan formulario, llaman al servicio, redirigen)
      ▲
 Servicios (services.py: casos de uso, transacciones, reglas de negocio)
      ▲
  Modelos  (models.py: persistencia, invariantes, constraints)
      ▲
PostgreSQL (triggers y constraints como última defensa)
```

| Componente | Responsabilidad | Prohibido |
|---|---|---|
| `models.py` | Estructura, relaciones, constraints, `clean()` de invariantes locales | Llamar a otros servicios, enviar correos, generar asientos |
| `services.py` | Casos de uso completos, `transaction.atomic`, bloqueo de filas, orquestación contable | Devolver QuerySets, contener HTML |
| `selectors.py` | Consultas de lectura y reportes | Escribir en base de datos |
| `forms.py` | Validación de entrada del usuario | Reglas de negocio financieras |
| `views.py` | Orquestar petición/respuesta y permisos | Calcular intereses, mora o asientos |
| Plantillas | Presentación | Cálculo de dinero |

**Contabilidad transversal:** ningún módulo crea asientos a mano. Todos invocan
`apps.contabilidad.services.contabilizar(evento, ...)`, que resuelve las cuentas y las
fórmulas a partir de `PlantillaAsiento` / `PlantillaLinea` y valida `débitos = créditos`
antes de confirmar.

---

## 5. Manejo del dinero

```python
# apps/core/dinero.py
from decimal import Decimal, ROUND_HALF_UP

CENTIMO = Decimal("0.01")
CERO = Decimal("0.00")

def cuantizar(valor: Decimal) -> Decimal:
    """Redondea a 2 decimales con HALF_UP. Única puerta de redondeo del sistema."""
    return Decimal(valor).quantize(CENTIMO, rounding=ROUND_HALF_UP)

def a_decimal(valor: str | int | Decimal) -> Decimal:
    """Convierte a Decimal SIEMPRE desde str. Prohibido construir Decimal desde float."""
```

Reglas no negociables:

1. Todo campo monetario es `DecimalField(max_digits=18, decimal_places=2)` → `NUMERIC(18,2)`.
2. Prohibido `float` en cualquier cálculo, incluidos los intermedios.
3. El redondeo ocurre **una sola vez**, al final de cada cálculo, mediante `cuantizar()`.
4. En repartos (cuota, prorrateo de intereses) se usa `repartir(total, n)`: calcula `n-1` partes
   iguales cuantizadas y asigna a la última parte el residuo `total - suma(anteriores)`, de modo
   que `Σ partes == total` con exactitud de centavos.
5. Total de un asiento: `suma(débitos) == suma(créditos)` comparado como `Decimal`, no con tolerancia.
6. Ruff prohíbe `float` en módulos financieros mediante regla de lint y revisión en CI.

---

## 6. Transacciones, concurrencia e idempotencia

| Mecanismo | Implementación |
|---|---|
| Atomicidad | Toda operación financiera envuelta en `@transaction.atomic` en la capa de servicios |
| Bloqueo de filas | `select_for_update()` sobre cuentas de ahorro, préstamos, cuotas, turnos de caja y secuencias documentales |
| Orden de bloqueo | Siempre por `id` ascendente cuando se bloquean varias filas, para evitar interbloqueos |
| Idempotencia | Cada formulario financiero lleva `clave_idempotencia` (UUID); la tabla `OperacionIdempotente` tiene índice único y rechaza el segundo posteo |
| Consecutivos | `SecuenciaDocumental` bloqueada con `select_for_update()`; jamás se usan `max(id)+1` ni `count()+1` |
| Reintentos | En caso de `OperationalError` por interbloqueo se reintenta la transacción completa (máximo 3 veces) |
| Aislamiento | `READ COMMITTED` (por defecto) + bloqueo explícito de filas donde hay concurrencia real |

---

## 7. Inmutabilidad y auditoría

1. **Modelo base inmutable:** `apps.core.models.InmutableModel` sobrescribe `save()` y `delete()`
   para rechazar modificaciones cuando el registro está en estado confirmado/contabilizado, y
   rechazar siempre el borrado.
2. **Sin borrados en cascada:** todas las claves foráneas financieras usan `on_delete=PROTECT`.
3. **Defensa en profundidad:** migración con `RunSQL` que instala un trigger en
   `contabilidad_lineaasiento` que rechaza `UPDATE` y `DELETE` cuando el asiento está confirmado.
4. **Bitácora de auditoría** (`apps.auditoria`): una fila por cambio, con usuario, fecha, IP,
   user-agent, acción, app, modelo, id afectado, valores anteriores y nuevos en `JSONB`, motivo y
   **cadena de hash SHA-256** (`hash_registro = sha256(hash_anterior + contenido)`), lo que permite
   demostrar que nadie alteró el historial. Un comando `verificar_cadena_auditoria` recalcula la
   cadena completa.
5. **Reversos:** un asiento confirmado nunca se edita. El servicio `reversar_asiento()` crea el
   asiento espejo, marca el original como `REVERSADO` y deja referencia cruzada entre ambos.

---

## 8. Contabilización dirigida por datos

| Modelo | Función |
|---|---|
| `PlantillaAsiento` | Define el evento contable (`DEPOSITO_AHORRO`, `RETIRO_AHORRO`, `DESEMBOLSO_PRESTAMO`, `PAGO_CUOTA`, `DEVENGOS_INTERES`, `MORA_GENERADA`, `PROVISION_CARTERA`, …) |
| `PlantillaLinea` | Define cada línea: cuenta contable, tipo de movimiento (débito/crédito) y fórmula del monto (`monto`, `capital`, `interes`, `mora`, `monto - comision`, …) |

Ventajas: cambiar una cuenta contable es configuración auditada, no un despliegue de código; y el
catálogo de reglas queda documentado y verificable por el contador.

---

## 9. Tareas programadas (django-q2, broker ORM)

| Tarea | Frecuencia | Notas |
|---|---|---|
| `devengar_intereses_ahorro` | Diaria/mensual | Alimenta `SaldoDiarioAhorro` y calcula el interés del período |
| `acreditar_intereses_ahorro` | Mensual | Asiento de pasivo → depósito del socio |
| `devengar_intereses_prestamo` | Diaria | Interés corrido por cuota, según `interes_total / nº cuotas` |
| `generar_mora` | Diaria | Aplica la política D-03 después de los 3 días de gracia |
| `reclasificar_cartera_vencida` | Diaria | Traslado por tramos de antigüedad |
| `calcular_provision_cartera` | Mensual | Según tabla de porcentajes (pendiente P-05) |
| `cierre_diario` | Fin de jornada | Consolida turnos de caja y bloquea el día |
| `verificar_cuadre` | Diaria | Débitos = créditos, saldos derivados vs. caché, cartera vs. auxiliares |

Todas las tareas son **idempotentes y re-ejecutables**: si se corren dos veces, no duplican asientos.

---

## 10. Reportes

- **PDF:** plantilla HTML con membrete → WeasyPrint. *Advertencia:* WeasyPrint requiere GTK en
  Windows; por eso la generación de PDF se ejecuta en Docker/Linux. En desarrollo nativo se puede
  usar el contenedor de producción para probar los PDF.
- **Excel:** openpyxl, con hoja de parámetros y sello de tiempo para trazabilidad.
- **Trazabilidad:** cada reporte emitido se registra en `ReporteGenerado` (tipo, parámetros,
  usuario, fecha, hash del archivo). Un reporte emitido es reproducible: mismos parámetros,
  mismo resultado.
- **Filtros** por fecha, sucursal y usuario en todos los reportes que lo admitan.

---

## 11. Seguridad

| Control | Implementación |
|---|---|
| Contraseñas | Argon2 (`PASSWORD_HASHERS`), longitud mínima 12, verificación contra lista de comunes |
| Sesiones | Expiración por inactividad (`SESSION_COOKIE_AGE` + `SESSION_SAVE_EVERY_REQUEST`), cierre al cambiar contraseña |
| Intentos de acceso | Bloqueo temporal tras 5 intentos fallidos, registro en `IntentoAcceso` |
| 2FA | Opcional (TOTP), recomendado y activado por defecto para Administrador y Contador |
| CSRF | Token en todos los formularios, incluidos los fragmentos HTMX |
| Autorización | Permisos por rol a nivel de servicio (no solo vistas) + `login_required`/`permission_required` |
| Producción | HTTPS obligatorio, HSTS, `SECURE_*`, cookies `Secure`/`HttpOnly`/`SameSite`, CSP |
| Secretos | `django-environ`; `.env` fuera del repositorio; `.env.example` sin valores reales |
| Datos personales | Acceso a cédulas, ingresos y direcciones restringido por rol; toda consulta sensible queda auditada |
| Respaldos | `pg_dump` cifrado con `age`, retención 30 días, copia externa, restauración probada mensualmente |

---

## 12. Pruebas y CI

| Nivel | Alcance | Herramientas |
|---|---|---|
| Unitarias de cálculo | Interés de ahorro (saldo promedio diario), interés flat, tabla de amortización, mora acumulada, reparto de centavos | `pytest`, `hypothesis` (pruebas basadas en propiedades) |
| Integración | Servicios + asientos: `Σ débitos = Σ créditos`, saldos derivados, inmutabilidad, reversos | `pytest-django`, `factory_boy` |
| Concurrencia | Dos retiros simultáneos sobre la misma cuenta, dos desembolsos con la misma secuencia | `TransactionTestCase`, hilos |
| Cuadre | Comparación entre saldos derivados de asientos y saldos en caché | Comando `verificar_cuadre` |
| Extremo a extremo | Flujo por rol: cajero → depósito; oficial → solicitud → aprobación → desembolso → pago | `pytest` + `Client` |
| Cobertura | **≥90 % en `contabilidad`, `ahorros`, `prestamos` (módulos de cálculo)** | `pytest-cov`, falla el CI si baja |

**CI (GitHub Actions):** servicios PostgreSQL 16, `ruff check`, `black --check`, `pytest --cov`,
`makemigrations --check --dry-run` (impide migraciones sin generar).

---

## 13. Despliegue y respaldos

```
Internet → Nginx (HTTPS, TLS, límites) → Gunicorn (Django) → PostgreSQL 16
                                      ↘ archivos estáticos / media
                                      ↘ tarea programada (django-q2)
                                      ↘ contenedor de respaldo (pg_dump cifrado)
```

- `docker-compose.prod.yml`: servicios `web`, `db`, `nginx`, `qcluster`, `backup`.
- Migraciones al desplegar, con verificación previa del respaldo.
- Variables de entorno en `.env` del servidor (permisos 600), nunca en la imagen.
- Ventana de mantenimiento acordada; el sistema opera en línea durante la jornada.
- Respaldo: diario, cifrado, verificado por tamaño y `pg_restore --list`; **prueba de restauración
  mensual documentada con acta**.

---

## 14. Riesgos técnicos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| WeasyPrint sin GTK en Windows | Generar PDF dentro de Docker; probar en el contenedor |
| Descuadres por redondeo | `cuantizar()` única, `repartir()` con residuo controlado, pruebas de propiedad |
| Doble posteo por doble clic | Idempotencia + botones deshabilitados en HTMX |
| Bloqueos y tiempos de espera | Bloqueo ordenado por id, transacciones cortas, reintentos limitados |
| Crecimiento de la bitácora | Particionado por año y archivado cifrado; nunca se borra |
| Complejidad de la contabilidad dirigida por datos | Pruebas de cuadre por evento y validación con el contador |
| Migración desde Excel con datos sucios | Etapa de staging, validación de cédulas y saldos, conciliación firmada |
