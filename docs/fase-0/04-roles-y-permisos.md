# COOPGESTION — Matriz de roles y permisos

| Campo | Valor |
|---|---|
| Documento | Roles, permisos, segregación de funciones y doble aprobación |
| Versión | 1.0 |
| Fase | 0.3 |
| Estado | Propuesta para aprobación |

---

## 1. Roles definidos

| Código | Rol | Alcance | Descripción |
|---|---|---|---|
| `ADMIN` | Administrador | Total, con doble firma | Configura el sistema, gestiona usuarios y parámetros, autoriza excepciones. No puede aprobar sus propias operaciones |
| `CONTADOR` | Contador | Contabilidad y reportes | Asientos manuales, cierres, provisiones, libros, reportes contables y regulatorios |
| `OFICIAL` | Oficial de Préstamos | Cartera de crédito | Solicitudes, estudio, seguimiento de cobro y mora. **No aprueba ni desembolsa** |
| `CAJERO` | Cajero | Caja y operaciones de ventanilla | Depósitos, retiros autorizados, cobros de cuotas, apertura y cierre de su turno |
| `AUDITOR` | Auditor | **Solo lectura** | Consulta todo, incluida la bitácora. No ejecuta ninguna operación financiera |
| `COMITE` | Gerencia / Comité de Crédito | **Propuesto (P-13)** | Aprueba solicitudes de préstamo, retiros sobre umbral y ajustes. No digita operaciones de caja |

> **Propuesta:** el flujo aprobado en D10 (Oficial → Administración/Comité) exige que quien aprueba
> sea distinto de quien solicita. El sistema **siempre** bloquea la autoaprobación, aunque el rol
> `ADMIN` acumule ambas funciones. Si la cooperativa no crea el rol `COMITE`, el Administrador
> cumplirá la función de aprobador y quedará registrado como tal.

---

## 2. Matriz de permisos

Leyenda: **E** = ejecuta · **A** = aprueba (segunda firma) · **L** = solo lectura · **—** = sin acceso.

| Operación | ADMIN | CONTADOR | OFICIAL | CAJERO | AUDITOR | COMITE |
|---|---|---|---|---|---|---|
| **Socios** | | | | | | |
| Registrar y editar socio | E | L | E | L | L | L |
| Aprobar admisión de socio | A | — | — | — | L | E |
| Aprobar retiro o exclusión de socio | A | L | — | — | L | E |
| Consultar expediente y documentos | E | L | E | L | L | L |
| Ver cédula y datos personales sensibles | E | L | E | L | L | L |
| Registrar aportaciones (capital social) | E | L | — | E | L | — |
| Devolver aportaciones | A | L | — | — | L | E |
| **Ahorros** | | | | | | |
| Abrir cuenta de ahorro | E | L | E | E | L | — |
| Depositar | E | L | — | E | L | — |
| Retirar hasta RD$ 50,000 | E | L | — | E | L | — |
| Retirar más de RD$ 50,000 | A | L | — | — | L | A |
| Calcular y contabilizar intereses | E | E | — | — | L | — |
| Acreditar intereses en libretas | A | E | — | — | L | — |
| Reversar movimiento de ahorro | A | L | — | — | L | — |
| Ver estado de cuenta de un socio | E | E | E | E | L | L |
| **Préstamos** | | | | | | |
| Registrar solicitud de préstamo | E | — | E | — | L | — |
| Estudio y análisis de crédito | L | — | E | — | L | L |
| Aprobar o rechazar solicitud | A | — | — | — | L | E |
| Desembolsar préstamo | A | — | — | E | L | — |
| Registrar pago de cuota | E | L | — | E | L | — |
| Aplicar abono extraordinario | E | L | E | E | L | — |
| Condonar mora o cargos | A | A | — | — | L | E |
| Reestructurar o refinanciar | A | L | E | — | L | A |
| Castigar cartera | A | E | — | — | L | A |
| Generar y ajustar mora | E | E | L | — | L | — |
| **Caja** | | | | | | |
| Abrir turno de caja | E | — | — | E | L | — |
| Cerrar turno y arquear | E | L | — | E | L | — |
| Autorizar descuadre de caja | A | A | — | — | L | — |
| Registrar gasto menor de caja chica | E | A | — | E | L | — |
| **Contabilidad** | | | | | | |
| Crear asiento manual | E | E | — | — | L | — |
| Confirmar asiento manual | A | E | — | — | L | — |
| Reversar asiento | A | L | — | — | L | — |
| Abrir período contable | E | E | — | — | L | — |
| Cerrar mes o año | A | E | — | — | L | — |
| Registrar provisión de cartera | A | E | — | — | L | — |
| Consultar libro diario y mayor | E | E | L | — | L | L |
| **Reportes** | | | | | | |
| Reportes operativos (cartera, mora, arqueo) | E | E | E | L | L | L |
| Reportes contables y estados financieros | E | E | — | — | L | L |
| Reportes regulatorios (IDECOOP, DGII) | E | E | — | — | L | L |
| Exportar a PDF y Excel | E | E | E | L | L | L |
| **Administración y control** | | | | | | |
| Gestionar usuarios y roles | E | — | — | — | L | — |
| Modificar parámetros y tasas | E | A | — | — | L | — |
| Ver bitácora de auditoría | E | L | — | — | L | L |
| Verificar cadena de hash de auditoría | E | L | — | — | E | — |
| Ejecutar y restaurar respaldos | E | — | — | — | L | — |
| Anular comprobante | A | L | — | — | L | — |

---

## 3. Reglas de segregación de funciones (aplicadas en la capa de servicios)

1. **Nadie aprueba su propia operación.** `Aprobacion.solicitado_por != aprobado_por`, validado con
   constraint de base de datos y en el servicio.
2. **El Oficial de Préstamos no desembolsa ni cobra.** Registra y analiza; aprueba el Comité y
   desembolsa Caja con autorización.
3. **El Cajero no aprueba excepciones.** Faltantes, sobrantes y retiros sobre umbral requieren
   segunda firma.
4. **El Auditor nunca escribe.** Su rol es de solo lectura incluso en la API interna; el sistema
   rechaza cualquier intento de escritura y lo registra en la bitácora.
5. **El Contador no digita operaciones de ventanilla.** Su ámbito es la contabilidad y los cierres.
6. **Doble firma obligatoria** en: desembolsos de préstamos, reversos contables, retiros sobre
   RD$ 50,000, condonación de mora, castigo de cartera y autorización de descuadres de caja.
7. **Excepción documentada:** en una cooperativa de una sola sucursal y 10 usuarios puede ocurrir
   que una persona acumule roles. Cuando eso pase, el sistema lo permite **pero deja constancia en
   la bitácora** y el Auditor debe revisar esas operaciones. Se recomienda que la persona que
   acumula roles no sea simultáneamente Cajero y Contador.

---

## 4. Parámetros de autorización (configurables)

| Parámetro | Valor inicial | Dónde se cambia |
|---|---|---|
| Umbral de retiro con doble firma | RD$ 50,000.00 | `ParametroSistema.UMBRAL_RETIRO_DOBLE_FIRMA` |
| Desembolsos con doble firma | Siempre (100 %) | `ParametroSistema.DOBLE_FIRMA_DESEMBOLSO` |
| Reversos con doble firma | Siempre (100 %) | `ParametroSistema.DOBLE_FIRMA_REVERSO` |
| Intentos fallidos antes de bloqueo | 5 | `ParametroSistema.INTENTOS_LOGIN` |
| Duración del bloqueo | 15 minutos | `ParametroSistema.MINUTOS_BLOQUEO` |
| Expiración de sesión por inactividad | 30 minutos | `SESSION_COOKIE_AGE` |
| 2FA obligatorio | No (recomendado para ADMIN y CONTADOR) | `ParametroSistema.2FA_OBLIGATORIO` |
| Emisión de NCF | **Desactivada** hasta tener RNC y autorización DGII | `ParametroSistema.EMISION_NCF_ACTIVA` |
| Días de gracia de mora | 3 | `ProductoPrestamo.dias_gracia_mora` |
| Porcentaje de mora por período | 5 % de la cuota total | `ProductoPrestamo.porcentaje_mora_periodo` |
| Tope máximo de mora acumulada | Pendiente de definición (P-10) | `ProductoPrestamo.tope_mora` |

---

## 5. Implementación técnica de los permisos

| Nivel | Mecanismo |
|---|---|
| Rol | Modelo `Rol` propio + `Group` de Django espejo para aprovechar `permission_required` |
| Vista | `LoginRequiredMixin` + `PermissionRequiredMixin` con permisos por acción (`ahorros.retirar`, `prestamos.aprobar`) |
| Servicio | **Verificación obligatoria**: cada servicio recibe el usuario y valida el permiso antes de tocar datos. La autorización no depende solo de la vista |
| Objeto | Reglas por objeto: el Oficial solo ve sus solicitudes asignadas; el Cajero solo su propio turno |
| Registro | Todo rechazo de permiso se registra en la bitácora con el usuario, la operación y el objeto |
| Pruebas | Suite de pruebas por rol que verifica permitidos **y prohibidos** (una prueba por cada celda con `—` de la matriz) |

---

## 6. Manual por rol (base para la Fase 7)

| Rol | Tareas diarias típicas |
|---|---|
| **Administrador** | Revisar bitácora, aprobar desembolsos y reversos, gestionar usuarios, revisar cuadre de caja del día |
| **Contador** | Verificar asientos automáticos, contabilizar intereses y mora, provisionar cartera, cerrar el mes, emitir estados financieros |
| **Oficial de Préstamos** | Registrar solicitudes, analizar capacidad de pago, dar seguimiento a la cartera y a la mora, gestionar cobros |
| **Cajero** | Abrir turno, recibir depósitos y pagos, pagar retiros autorizados, cerrar y arquear la caja |
| **Auditor** | Revisar la bitácora, verificar la cadena de hash, comparar saldos derivados con los estados, revisar operaciones con roles acumulados |
| **Gerencia / Comité** | Aprobar créditos, autorizar retiros sobre umbral y condonaciones |
