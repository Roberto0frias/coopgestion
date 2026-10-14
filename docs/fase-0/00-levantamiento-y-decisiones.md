# COOPGESTION — Fase 0 · Levantamiento y decisiones

| Campo | Valor |
|---|---|
| Documento | Acta de levantamiento y decisiones de diseño |
| Versión | 1.0 |
| Fase | 0 — Levantamiento y diseño |
| Responsable funcional | Roberto (Administración y Contabilidad de COOPGESTION) |
| Estado | Pendiente de aprobación de la Fase 0 |

---

## 1. Datos generales del proyecto

| Concepto | Dato |
|---|---|
| Nombre legal y comercial | COOPGESTION (Cooperativa de Ahorro y Crédito) |
| Tipo de cooperativa | CAC pura (solo ahorro y crédito) |
| RNC / registro IDECOOP | **En proceso de formalización** |
| Sucursales | 1 sucursal, caja única centralizada |
| Socios | 140 activos (34 plenos, 106 ahorrantes) |
| Transacciones estimadas | 20 a 50 diarias |
| Usuarios internos | 5 roles, ~10 usuarios concurrentes |
| Moneda | DOP exclusiva (soporte futuro para otras monedas) |
| Ejercicio fiscal | Enero a diciembre |
| Sistema de origen | Hojas de cálculo Excel (migración de 140 socios y saldos de apertura) |
| Repositorio | `coopgestion-core`, ramas `main` y `develop`, un commit por subfase |
| Entorno de desarrollo | PostgreSQL 16 nativo en Windows + `docker-compose.yml` para producción |
| Entorno de producción | VPS Linux con Docker (Django + PostgreSQL 16 + Nginx + HTTPS) |
| Plazo objetivo | 3 a 6 meses |

---

## 2. Resumen del levantamiento por bloque

| Bloque | Definición acordada |
|---|---|
| **A. Identidad y alcance** | CAC pura, 1 sucursal con caja centralizada, 140 socios, partida doble bajo normativa IDECOOP |
| **B. Socios y aportaciones** | Cédula obligatoria; capital social (patrimonio) diferenciado de ahorros (pasivo); admisión/retiro por administración o consejo; documentos, referencias y verificación PEP; cuentas según tipo de socio |
| **C. Ahorros** | Dos productos: ahorro de socios plenos y ahorro de socios ahorrantes; tasas por política interna; saldo promedio diario, base 360; interés mensual contabilizado como pasivo y acreditado en libreta; libreta virtual con comprobante físico firmado; política de cuentas inactivas |
| **D. Préstamos** | Tres productos: voluntarias de proyectos sociales (2 % mensual), socios plenos (2 % mensual), socios ahorrantes (3 % mensual); interés simple (flat) sobre capital inicial; frecuencia semanal, quincenal o mensual; fiador solidario; exento de ITBIS (a validar); mora 5 % con 3 días de gracia; flujo Oficial → Administración/Comité; desembolso por transferencia o cheque/efectivo |
| **E. Contabilidad** | Grupos 1 Activo, 2 Pasivo, 3 Patrimonio, 4 Ingresos, 5 Costos y Gastos (+ 6 Cuentas de orden propuesto); sucursal única; cierre de caja diario; cierre mensual con asientos de ajuste; provisiones por antigüedad; comprobantes y reportes preparados para IDECOOP/DGII |
| **F. Caja y tesorería** | Fondo fijo por cajero, arqueo diario con desglose de denominaciones; efectivo y transferencias; cuentas bancarias con doble firma; caja chica aprobada por Contador/Administrador |
| **G. Reportes** | Operativos, contables, gerenciales y regulatorios; exportación en PDF y Excel con membrete |
| **H. Usuarios y seguridad** | Administrador, Contador, Oficial de Préstamos, Cajero, Auditor (solo lectura); expiración de sesión; contraseña fuerte; 2FA opcional; separación estricta de funciones |
| **I. Infraestructura** | Docker + PostgreSQL en servidor local/VPS; operación web centralizada **sin modo offline**; respaldos diarios cifrados |
| **J. Migración** | Carga de 140 socios y saldos iniciales desde Excel; paralelo de 15 a 30 días; acta de saldos firmada por Contador y Administrador; capacitación por rol |

---

## 3. Decisiones confirmadas en la ronda de precisión

| # | Tema | Decisión |
|---|---|---|
| D-01 | Interés de préstamo (método flat) | El plazo se pacta **en meses**; solo cambia la frecuencia de pago. `interés_total = capital × tasa_mensual × nº de meses` |
| D-02 | Equivalencia de frecuencias | Mensual = 1 mes; quincenal = 0,5 mes; semanal = 0,25 mes (1 mes = 4 semanas). Por tanto 12 cuotas semanales = 3 meses |
| D-03 | Mora | 5 % sobre **la cuota total (capital + interés)**, **acumulable por cada período transcurrido** desde el vencimiento, con 3 días de gracia |
| D-04 | Interés de ahorro | **Saldo promedio diario, base 360**: `interés = Σ(saldo diario) × tasa_anual / 360` |
| D-05 | Voluntarias de proyectos | Se registran como **socias de tipo AHORRANTE** con bandera de participación en proyecto social |
| D-06 | Entorno de desarrollo | PostgreSQL 16 nativo en Windows para trabajar de inmediato + `docker-compose.yml` versionado para producción |
| D-07 | Doble aprobación | **Desembolsos y reversos: 100 % de los casos.** Retiros en efectivo sobre RD$ 50,000. Umbrales configurables |
| D-08 | Comprobantes fiscales | **NCF desactivado** (`EMISION_NCF_ACTIVA = false`) hasta que existan RNC y autorización de la DGII. El modelo se construye **NCF-ready** para activarlo sin retrabajo (confirmado por el responsable) |
| D-09 | Roles de base de datos | Dos roles: `postgres` (superusuario, solo administración) y `coopgestion` (aplicación: `NOSUPERUSER`, `NOCREATEROLE`). `CREATEDB` solo en desarrollo para la base de pruebas |
| D-10 | Residuo de centavos | El residuo de cada componente (capital e interés) se concentra en la última cuota. La base de reparto se calcula con redondeo **hacia abajo**, para que ninguna cuota pueda resultar negativa |
| D-11 | Entorno de desarrollo | PostgreSQL 16.15 portable en `127.0.0.1:5433`, en el perfil del usuario y sin permisos de administrador. La instalación previa de PostgreSQL 18.6 en el puerto 5432 se deja intacta |

---

## 4. Valores por defecto adoptados (no contradichos por el levantamiento)

| Tema | Valor adoptado |
|---|---|
| Precisión monetaria | `Decimal(18,2)` / `NUMERIC(18,2)`, `ROUND_HALF_UP`; prohibido `float` |
| Zona horaria y formato | `America/Santo_Domingo`; fechas `dd/mm/aaaa`; montos `RD$ 1,234.56` |
| Redondeo de cuota | Cuota = `(capital + interés_total) / nº cuotas` con `HALF_UP`; el residuo de centavos se ajusta en la última cuota, de modo que `Σ cuotas = capital + interés_total` exacto |
| Aportaciones | Patrimonio (capital social), grupo 3, separadas de los depósitos de ahorro (grupo 2) |
| Base de causación | Devengo (accrual): los intereses de préstamos y de ahorros se devengan y se contabilizan por período, no al cobro |
| Cierres | Diario: corte de caja al final de la jornada. Mensual: cierre contable con asientos de ajuste. Un período cerrado solo se corrige por asiento de reverso |
| Roles base | Administrador, Contador, Oficial de Préstamos, Cajero, Auditor (solo lectura) + **propuesta** de rol Gerencia/Comité de Crédito como aprobador |
| Seguridad | Sesión con expiración, contraseña fuerte, bloqueo por intentos fallidos, **2FA opcional** (recomendado para Administrador y Contador) |
| Respaldos | `pg_dump` diario cifrado, retención 30 días, copia fuera del servidor, restauración de prueba mensual documentada |
| Auditoría | Bitácora inmutable con cadena de hash: quién, qué, cuándo, desde dónde, valor anterior y nuevo |

---

## 5. Puntos abiertos, supuestos y bloqueos

> Ninguno de estos puntos impide iniciar la Fase 1. Los marcados como **BLOQUEO** sí detienen la fase indicada.

| ID | Tema | Impacto / fase | Responsable | Estado |
|---|---|---|---|---|
| P-01 | RNC e inscripción IDECOOP en trámite | **BLOQUEO para emitir NCF** (Fase 6) | Roberto / DGII | Abierto |
| P-02 | Tipos de NCF aplicables a ingresos exentos, secuencias autorizadas y obligatoriedad de e-CF | Fase 2 y 6 | Contador / DGII | Abierto |
| P-03 | No hay contador designado: validar catálogo de cuentas, provisiones, retenciones y exención de ITBIS | Fases 2, 5 y 6 | Roberto | Abierto |
| P-04 | Tasas de interés de ahorro por tipo de cuenta (valores iniciales) | Fase 4 | Administración | Abierto |
| P-05 | Tabla de porcentajes de provisión de cartera por antigüedad | Fase 2 y 5 | Contador | Abierto |
| P-06 | Listado de formularios y frecuencia de reportes IDECOOP | Fase 6 | Roberto / IDECOOP | Abierto |
| P-07 | Archivos Excel de origen: estructura, columnas y calidad de datos | Fase 8 | Administración | Abierto |
| P-08 | Fecha de corte para los saldos de apertura | Fase 8 | Contador / Administración | Abierto |
| P-09 | Política de suspensión de causación de intereses en cartera vencida (propuesta: 90 días) | Fase 2 y 5 | Contador | Abierto |
| P-10 | Tope de mora acumulada y validación legal del 5 % por período | **Riesgo legal** | Abogado / Contador | Abierto |
| P-11 | ¿Cuota de admisión o membresía? ¿Distribución de excedentes anuales? ¿Certificados de aportación? | Fases 3 y 6 | Administración / Asamblea | Abierto |
| P-12 | Antigüedad para declarar cuenta inactiva o dormida y proceso de reactivación | Fase 4 | Administración | Abierto |
| P-13 | ¿Se crea el rol Gerencia/Comité de Crédito como aprobador distinto del Oficial? | Fase 1 | Roberto | Abierto |
| P-14 | Base de mora cuando la cuota está parcialmente pagada (propuesta: saldo insoluto de la cuota) | Fase 5 | Contador | Abierto |
| P-15 | ¿La tasa del 2 % de voluntarias se determina por producto o por bandera de proyecto? | Fase 5 | Administración | Abierto |
| P-16 | Alícuotas de reserva legal, educación y asistencia social (3-2) | Fase 2 | Contador | Abierto |
| P-17 | Tratamiento de ITBIS en comisiones y de retenciones de ISR, si aplican | Fases 2 y 6 | Contador / DGII | Abierto |

---

## 6. Riesgos identificados y su tratamiento

| Riesgo | Tipo | Tratamiento acordado |
|---|---|---|
| Emitir NCF sin RNC ni autorización DGII | Legal | Se implementa el modelo fiscal (**NCF-ready**) con interruptor `EMISION_NCF_ACTIVA` en `false`. No se emite ningún comprobante fiscal hasta que existan RNC y secuencias autorizadas |
| Mora del 5 % acumulable por período: ≈60 % anual en cuotas mensuales y ≈260 % anual en semanales sobre el valor de la cuota | Legal / financiero | Se implementa **configurable con tope máximo por operación** y se advierte por escrito. Requiere validación de abogado y contador antes de operar con dinero real |
| Exención de ITBIS asumida "conforme a la ley cooperativa" | Fiscal | No se codifica ninguna alícuota como verdad legal: el tratamiento queda en parámetros y marcado como pendiente de validación |
| Cálculo flat ambiguo en frecuencias no mensuales | Financiero | Resuelto en D-01/D-02: `meses = cuotas × factor` (1 / 0,5 / 0,25) |
| Descuadre por redondeo de centavos | Financiero | Residuo concentrado en la última cuota; `Σ cuotas` debe ser exactamente igual a capital + interés total |
| Doble posteo por doble clic o reintento HTMX | Técnico | Clave de idempotencia única por operación y bloqueo de filas (`select_for_update`) |
| Falta de separación de funciones con solo 5 roles y 10 usuarios en una sucursal | Control interno | Doble firma obligatoria en desembolsos y reversos; bitácora inmutable revisada por el Auditor; el sistema impide aprobar la propia operación |
| Dependencia de una sola persona (Roberto) | Operativo | Documentación por rol, manuales y respaldos con procedimiento de restauración probado |
| Sin modo offline | Operativo | Decisión consciente: se prioriza la integridad contable sobre la disponibilidad |
