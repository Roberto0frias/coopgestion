# COOPGESTION — Catálogo de cuentas contables inicial

| Campo | Valor |
|---|---|
| Documento | Catálogo de cuentas y reglas de contabilización |
| Versión | 1.0 |
| Fase | 0.3 |
| Base | Partida doble, grupos 1 Activo · 2 Pasivo · 3 Patrimonio · 4 Ingresos · 5 Costos y Gastos · 6 Cuentas de orden |
| Estado | **Propuesta técnica pendiente de validación por un contador** (punto abierto P-03) |

> ⚠️ **Advertencia:** este catálogo es una propuesta profesional elaborada a partir del levantamiento.
> No constituye un catálogo oficial de IDECOOP ni sustituye la opinión de un contador público.
> Ninguna alícuota, porcentaje de reserva ni tratamiento fiscal se ha codificado como verdad legal.

---

## 1. Estructura de codificación

`G-SS-RR-CC` → Grupo · Subgrupo · Rubro · Cuenta. Ejemplo: `1-2-01-01` = Activo · Cartera de créditos · Cartera vigente · Préstamos a voluntarias.

| Nivel | Dígitos | Ejemplo | ¿Recibe movimientos? |
|---|---|---|---|
| Grupo | 1 | `1` | No |
| Subgrupo | 1 | `1-2` | No |
| Rubro | 2 | `1-2-01` | No |
| Cuenta | 2 | `1-2-01-01` | Sí |
| Subcuenta | 2 (opcional) | `1-2-01-01-01` | Sí |

Reglas: solo las cuentas de último nivel reciben asientos; `naturaleza` se deriva del grupo
(1 y 5 deudora; 2, 3 y 4 acreedora; 6 según el caso); las cuentas de valuación
(`1-2-04`, `1-4-04`) tienen naturaleza contraria a su grupo.

---

## 2. Grupo 1 — ACTIVO (naturaleza deudora)

| Código | Nombre | Notas |
|---|---|---|
| 1-1-01-01 | Caja general | Efectivo en la caja principal de la sucursal |
| 1-1-01-02 | Caja chica | Fondo para gastos menores |
| 1-1-01-03 | Caja por cajero (auxiliar) | Auxiliar por turno/cajero si se desea detalle por responsable |
| 1-1-02-01 | Banco — cuenta corriente | Cuenta operativa de la cooperativa |
| 1-1-02-02 | Banco — cuenta de ahorro institucional | — |
| 1-1-02-03 | Banco — cuenta de desembolsos | Cuenta con doble firma |
| 1-1-03-01 | Efectivo en tránsito | Traslados caja ↔ banco no confirmados |
| 1-2-01-01 | Préstamos vigentes — voluntarias de proyectos | Capital por producto |
| 1-2-01-02 | Préstamos vigentes — socios plenos | — |
| 1-2-01-03 | Préstamos vigentes — socios ahorrantes | — |
| 1-2-02-01 | Cartera vencida 1 a 30 días | Reclasificación por antigüedad |
| 1-2-02-02 | Cartera vencida 31 a 60 días | — |
| 1-2-02-03 | Cartera vencida 61 a 90 días | — |
| 1-2-02-04 | Cartera vencida 91 a 180 días | — |
| 1-2-02-05 | Cartera vencida 181 a 365 días | — |
| 1-2-02-06 | Cartera vencida más de 365 días | — |
| 1-2-03-01 | Intereses por cobrar sobre préstamos vigentes | Devengados no cobrados |
| 1-2-03-02 | Intereses por cobrar sobre préstamos vencidos | — |
| 1-2-03-03 | Mora por cobrar | Cargos por atraso generados y no cobrados |
| 1-2-04-01 | (–) Estimación para cartera 1 a 30 días | Cuenta de valuación, saldo acreedor |
| 1-2-04-02 | (–) Estimación para cartera 31 a 60 días | — |
| 1-2-04-03 | (–) Estimación para cartera 61 a 90 días | — |
| 1-2-04-04 | (–) Estimación para cartera 91 a 180 días | — |
| 1-2-04-05 | (–) Estimación para cartera 181 a 365 días | — |
| 1-2-04-06 | (–) Estimación para cartera más de 365 días | — |
| 1-3-01-01 | Cuentas por cobrar a empleados | — |
| 1-3-02-01 | Cuentas por cobrar a socios (otros conceptos) | — |
| 1-3-03-01 | Gastos pagados por anticipado | Seguros y papelería |
| 1-3-05-01 | Anticipos a proveedores | — |
| 1-3-06-01 | Otras cuentas por cobrar | — |
| 1-4-01-01 | Mobiliario y equipo de oficina | — |
| 1-4-02-01 | Equipos de cómputo | — |
| 1-4-03-01 | Vehículos | — |
| 1-4-04-01 | (–) Depreciación acumulada mobiliario y equipo | — |
| 1-4-04-02 | (–) Depreciación acumulada equipos de cómputo | — |
| 1-4-04-03 | (–) Depreciación acumulada vehículos | — |
| 1-5-02-01 | Software y licencias | — |
| 1-5-02-02 | (–) Amortización acumulada de intangibles | — |
| 1-5-03-01 | Otros activos | — |

## 3. Grupo 2 — PASIVO (naturaleza acreedora)

| Código | Nombre | Notas |
|---|---|---|
| 2-1-01-01 | Depósitos de ahorro — socios plenos | Obligación principal con los socios |
| 2-1-02-01 | Depósitos de ahorro — socios ahorrantes | — |
| 2-1-03-01 | Depósitos a plazo fijo | Preparada; no aplica en esta fase |
| 2-1-04-01 | Depósitos de ahorro programado o navideño | Preparada; no aplica en esta fase |
| 2-2-01-01 | Intereses por pagar sobre ahorros | Devengo mensual de ahorros |
| 2-2-01-02 | Intereses por pagar sobre depósitos a plazo | — |
| 2-3-01-01 | Préstamos bancarios por pagar — corto plazo | — |
| 2-3-02-01 | Préstamos bancarios por pagar — largo plazo | — |
| 2-3-03-01 | Intereses por pagar sobre préstamos bancarios | — |
| 2-4-01-01 | ISR retenido a terceros por pagar | Solo si aplica — validar con contador |
| 2-4-02-01 | Retenciones TSS por pagar | Solo si aplica |
| 2-4-03-01 | ITBIS por pagar | Solo si aplica |
| 2-4-04-01 | Otras retenciones y contribuciones | — |
| 2-5-01-01 | Proveedores por pagar | — |
| 2-5-02-01 | Gastos acumulados por pagar | — |
| 2-5-03-01 | Saldos a favor de socios (pagos adelantados) | Contrapartida de `SaldoFavor` |
| 2-5-04-01 | Otras cuentas por pagar | — |
| 2-7-01-01 | Intereses cobrados por anticipado | Solo si se cobrara interés por adelantado |

## 4. Grupo 3 — PATRIMONIO (naturaleza acreedora)

| Código | Nombre | Notas |
|---|---|---|
| 3-1-01-01 | Aportaciones de socios plenos | Capital social |
| 3-1-02-01 | Aportaciones de socios ahorrantes | Capital social |
| 3-1-03-01 | (–) Aportaciones suscritas no pagadas | Cuenta de naturaleza contraria |
| 3-2-01-01 | Reserva legal | Porcentaje pendiente de validación (P-16) |
| 3-2-02-01 | Reserva de educación cooperativa | Pendiente de validación (P-16) |
| 3-2-03-01 | Reserva de asistencia social | Pendiente de validación (P-16) |
| 3-2-04-01 | Otras reservas estatutarias | — |
| 3-3-01-01 | Excedentes (pérdidas) acumuladas de ejercicios anteriores | — |
| 3-3-02-01 | Excedente (pérdida) del ejercicio | Resultado del período |
| 3-3-03-01 | Excedentes por distribuir | Según decisión de asamblea |
| 3-4-02-01 | Donaciones y legados | — |

## 5. Grupo 4 — INGRESOS (naturaleza acreedora)

| Código | Nombre | Notas |
|---|---|---|
| 4-1-01-01 | Intereses sobre préstamos — voluntarias | 2 % mensual según levantamiento |
| 4-1-01-02 | Intereses sobre préstamos — socios plenos | 2 % mensual |
| 4-1-01-03 | Intereses sobre préstamos — socios ahorrantes | 3 % mensual |
| 4-1-04-01 | Ingresos por mora | Cargos por atraso devengados |
| 4-1-05-01 | Intereses sobre depósitos bancarios e inversiones | — |
| 4-1-06-01 | Comisiones por servicios | Solo si aplica |
| 4-2-01-01 | Cuotas de admisión o membresía | Pendiente de confirmar (P-11) |
| 4-2-02-01 | Multas y recargos distintos de mora | — |
| 4-2-04-01 | Recuperación de cartera castigada | — |
| 4-2-06-01 | Sobrantes de caja | Requiere autorización del Administrador |
| 4-2-05-01 | Otros ingresos | — |

## 6. Grupo 5 — COSTOS Y GASTOS (naturaleza deudora)

| Código | Nombre | Notas |
|---|---|---|
| 5-1-01-01 | Intereses sobre ahorros de socios | Gasto financiero principal |
| 5-1-01-02 | Intereses sobre depósitos a plazo | — |
| 5-1-03-01 | Intereses sobre préstamos bancarios | — |
| 5-1-04-01 | Comisiones bancarias | — |
| 5-2-01-01 | Sueldos y salarios | — |
| 5-2-01-02 | Bonificaciones y prestaciones | — |
| 5-2-01-03 | TSS e INFOTEP | — |
| 5-2-02-01 | Honorarios profesionales | Contador, abogado, auditoría |
| 5-2-03-01 | Servicios básicos | Energía, agua, telecomunicaciones, internet |
| 5-2-04-01 | Alquileres | — |
| 5-2-05-01 | Papelería, útiles y materiales | Incluye libretas y comprobantes |
| 5-2-06-01 | Combustible y transporte | — |
| 5-2-07-01 | Mantenimiento y reparaciones | — |
| 5-2-08-01 | Seguros | — |
| 5-2-09-01 | Depreciaciones | — |
| 5-2-10-01 | Gastos de educación cooperativa | — |
| 5-2-11-01 | Gastos de asistencia social | — |
| 5-2-12-01 | Gastos de asamblea y representación | — |
| 5-2-13-01 | Publicidad y promoción | — |
| 5-2-14-01 | Impuestos y tasas municipales | — |
| 5-2-15-01 | Gastos legales y notariales | — |
| 5-2-17-01 | Otros gastos generales | — |
| 5-3-01-01 | Provisión para cartera de créditos | Gasto del período |
| 5-3-02-01 | Castigo de cartera | Solo si se lleva contra resultado |
| 5-3-03-01 | Pérdidas por diferencias de caja (faltantes) | Requiere autorización |
| 5-3-04-01 | Ajustes y pérdidas diversas | — |
| 5-4-01-01 | Impuesto sobre la renta del ejercicio | Solo si aplica — validar exención |

## 7. Grupo 6 — CUENTAS DE ORDEN (control, sin efecto en resultados)

| Código | Nombre | Notas |
|---|---|---|
| 6-1-01-01 | Garantías recibidas — prendas e hipotecas | Valor estimado |
| 6-1-02-01 | Fiadores solidarios y montos garantizados | Respaldo de la cartera |
| 6-1-03-01 | Documentos y contratos en custodia | — |
| 6-1-04-01 | Cartera castigada en control | Memoria de cobro |
| 6-1-05-01 | Contingencias y litigios | — |

> **Nota de diseño:** el levantamiento definió cinco grupos (1 a 5). Se propone agregar el grupo 6
> para controlar garantías, fiadores y cartera castigada sin distorsionar el balance. Si la
> cooperativa prefiere no usarlo, se elimina sin afectar el resto del modelo.

---

## 8. Reglas de contabilización por evento

Formato: **evento → débito / crédito**. Todas las reglas se implementan como `PlantillaAsiento`
configurable (ver arquitectura §8) y son verificables por el contador sin tocar código.

| # | Evento | Débito | Crédito | Momento |
|---|---|---|---|---|
| 1 | Depósito en efectivo a ahorro | 1-1-01-01 Caja | 2-1-01-01 / 2-1-02-01 Depósitos | Al confirmar en caja |
| 2 | Depósito por transferencia | 1-1-02-01 Banco | 2-1-01-01 / 2-1-02-01 Depósitos | Al confirmar |
| 3 | Retiro en efectivo | 2-1-01-01 / 2-1-02-01 Depósitos | 1-1-01-01 Caja | Al confirmar |
| 4 | Aportación de capital social | 1-1-01-01 Caja o 1-1-02-01 Banco | 3-1-01-01 / 3-1-02-01 Aportaciones | Al recibir |
| 5 | Devolución de aportaciones | 3-1-01-01 / 3-1-02-01 | 1-1-01-01 Caja o Banco | Con aprobación |
| 6 | Devengo mensual de intereses de ahorro | 5-1-01-01 Intereses sobre ahorros | 2-2-01-01 Intereses por pagar | Último día del mes |
| 7 | Acreditación de intereses en la libreta | 2-2-01-01 Intereses por pagar | 2-1-01-01 / 2-1-02-01 Depósitos | Al acreditar |
| 8 | Desembolso de préstamo (efectivo) | 1-2-01-0x Préstamos vigentes | 1-1-01-01 Caja | Al desembolsar |
| 9 | Desembolso por transferencia | 1-2-01-0x Préstamos vigentes | 1-1-02-01 Banco | Al desembolsar |
| 10 | Desembolso acreditado en cuenta de ahorro | 1-2-01-0x Préstamos vigentes | 2-1-01-01 / 2-1-02-01 Depósitos | Al desembolsar |
| 11 | Devengo de interés de préstamo | 1-2-03-01 Intereses por cobrar | 4-1-01-0x Ingresos por intereses | Por cuota vencida o cierre de mes |
| 12 | Generación de mora | 1-2-03-03 Mora por cobrar | 4-1-04-01 Ingresos por mora | Al superar la gracia |
| 13 | Condonación de mora | 4-1-04-01 Ingresos por mora | 1-2-03-03 Mora por cobrar | Con doble autorización |
| 14 | Cobro de cuota en efectivo | 1-1-01-01 Caja | 1-2-01-0x (capital), 1-2-03-01 (interés), 1-2-03-03 (mora) | Al recibir el pago |
| 15 | Cobro por transferencia | 1-1-02-01 Banco | Mismas cuentas del evento 14 | Al confirmar |
| 16 | Pago anticipado no aplicado a cuotas | 1-1-01-01 Caja | 2-5-03-01 Saldos a favor de socios | Al recibir |
| 17 | Aplicación posterior de saldo a favor | 2-5-03-01 Saldos a favor | 1-2-01-0x, 1-2-03-01, 1-2-03-03 | Al aplicar |
| 18 | Reclasificación de cartera vencida | 1-2-02-0x Cartera vencida | 1-2-01-0x Préstamos vigentes | Diaria |
| 19 | Provisión de cartera del período | 5-3-01-01 Provisión | 1-2-04-0x Estimación | Mensual |
| 20 | Castigo de cartera | 1-2-04-0x Estimación | 1-2-01-0x / 1-2-02-0x Cartera | Con aprobación |
| 21 | Recuperación de cartera castigada | 1-1-01-01 Caja | 4-2-04-01 Recuperación | Al cobrar |
| 22 | Apertura de turno con fondo desde banco | 1-1-01-01 Caja | 1-1-02-01 Banco | Al retirar el fondo |
| 23 | Depósito de efectivo al banco | 1-1-02-01 Banco | 1-1-01-01 Caja | Al depositar |
| 24 | Faltante de caja autorizado | 5-3-03-01 Pérdidas por faltantes | 1-1-01-01 Caja | Al cerrar el turno |
| 25 | Sobrante de caja autorizado | 1-1-01-01 Caja | 4-2-06-01 Sobrantes de caja | Al cerrar el turno |
| 26 | Gasto menor de caja chica | 5-2-xx-xx según concepto | 1-1-01-02 Caja chica | Con comprobante aprobado |
| 27 | Reverso de cualquier asiento | Cuentas originales acreditadas | Cuentas originales debitadas | Con doble autorización |
| 28 | Cierre mensual de resultados | 4-xxxx Ingresos | 3-3-02-01 Excedente del ejercicio | Fin de mes |
| 29 | Cierre mensual de resultados (gastos) | 3-3-02-01 Excedente del ejercicio | 5-xxxx Costos y gastos | Fin de mes |
| 30 | Cierre anual | 3-3-02-01 Excedente del ejercicio | 3-3-01-01 Excedentes acumuladas | Al cerrar el año |

---

## 9. Políticas contables aplicadas

| Política | Definición |
|---|---|
| Base de contabilización | **Devengo**: ingresos y gastos se reconocen cuando se generan, no cuando se cobran o pagan |
| Interés de préstamos | Método flat: `interés_total = capital × tasa_mensual × nº de meses`; se devenga en partes iguales por cuota (`interés_total / nº cuotas`) |
| Interés de ahorros | Saldo promedio diario, base 360: `Σ(saldo diario) × tasa_anual / 360`; se devenga el último día del mes |
| Mora | 5 % de la cuota total por cada período transcurrido tras 3 días de gracia; se reconoce como ingreso al generarse, con **tope máximo configurable** (P-10) |
| Suspensión de causación | Propuesta: suspender el reconocimiento de intereses al pasar a cartera vencida por más de 90 días y reconocerlos al cobro (P-09) |
| Provisión de cartera | Por antigüedad de saldos, con porcentajes definidos por la administración y el contador (P-05) |
| Redondeo | `ROUND_HALF_UP` a 2 decimales; el residuo se concentra en la última cuota para que la suma sea exacta |
| Inmutabilidad | Los asientos confirmados no se editan ni se borran: se corrigen con asiento de reverso |
| Cierre de períodos | Un mes cerrado no admite asientos nuevos; cualquier corrección se hace en un período abierto con asiento de reverso |

---

## 10. Pendientes que debe resolver el contador antes de operar con dinero real

1. Validar la estructura y los nombres del catálogo (P-03).
2. Definir la tabla de porcentajes de provisión por antigüedad (P-05).
3. Confirmar la suspensión de causación de intereses en cartera vencida (P-09).
4. Confirmar el tratamiento de ITBIS y la exención invocada en el levantamiento (P-17).
5. Confirmar alícuotas de reserva legal, educación y asistencia social (P-16).
6. Confirmar si existe cuota de admisión o membresía (P-11) y su cuenta contable.
7. Confirmar el tope legal de la mora acumulada (P-10).
