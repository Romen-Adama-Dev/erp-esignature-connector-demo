# Registro RAID para el paso a producción

Riesgos, supuestos, incidencias y dependencias del caso de estudio. Probabilidad e impacto en escala baja, media y alta. Se revisa en el seguimiento semanal y antes de cada comité de paso.

## Riesgos

| ID | Riesgo | Prob. | Impacto | Responsable | Mitigación | Estado |
|----|--------|-------|---------|-------------|------------|--------|
| R1 | El proveedor de firma limita las peticiones por minuto y un pico de fin de mes provoca rechazos 429 | Media | Media | Desarrollo | Lotes acotados, 429 tratado como transitorio con espera exponencial y prueba de carga en el piloto | Abierto |
| R2 | Un reenvío tras una caída crea un sobre duplicado y el firmante recibe dos solicitudes | Media | Alta | PM técnico | Clave de idempotencia por documento y versión (ADR-003), con test de caída entre envío y escritura | Mitigado |
| R3 | Los logs o diagnósticos acaban guardando nombres o correos de firmantes | Media | Alta | PM técnico | Campos fijos en diagnósticos, `sanitize()` en el log y revisión del DPO antes del go-live | Mitigado |
| R4 | El ERP no responde durante la escritura de vuelta y quedan sobres que el ERP desconoce | Baja | Media | Desarrollo | La ejecución se aborta si el ERP falla; la idempotencia recupera el sobre en la siguiente | Mitigado |
| R5 | Administración no tiene tiempo para el piloto en las semanas de cierre contable | Alta | Media | PM técnico | Piloto fuera de cierre, sesiones de una hora reservadas con antelación | Abierto |
| R6 | Un documento sin correo de firmante bloquea la cola | Media | Baja | Responsable ERP | Error permanente sin reintento, estado `error` visible en el ERP y validación del campo en origen | Abierto |

## Supuestos

| ID | Supuesto | Responsable | Cómo se comprueba |
|----|----------|-------------|-------------------|
| A1 | La API de firma acepta una cabecera de idempotencia o permite consultar sobres por referencia externa | Desarrollo | Revisión de la API en el paquete 2.2 |
| A2 | El ERP permite exponer la cola de documentos y actualizar el estado por API | Responsable ERP | Contrato de datos del paquete 2.3 |
| A3 | El volumen es de unas pocas decenas de documentos al día, con picos a fin de mes | Usuarios clave | Inventario del paquete 2.1 |
| A4 | Hay un sandbox del proveedor de firma con el mismo comportamiento de errores que producción | PM técnico | Pruebas de fallo del paquete 5.3 |

## Incidencias

| ID | Incidencia | Fecha | Responsable | Acción | Estado |
|----|------------|-------|-------------|--------|--------|
| I1 | En el piloto, varios contratos llegan con el correo del firmante vacío | Semana 6 | Responsable ERP | Campo obligatorio en el ERP para los tipos que se firman | Cerrada |
| I2 | El sandbox del proveedor devuelve 503 intermitentes por las tardes | Semana 6 | Desarrollo | Confirmado con el proveedor; los reintentos lo absorben y queda anotado en el informe | Cerrada |

Las incidencias son parte del caso simulado, no de un proyecto real.

## Dependencias

| ID | Dependencia | De quién | Necesaria para | Fecha límite | Estado |
|----|-------------|----------|----------------|--------------|--------|
| D1 | Credenciales de sandbox del proveedor de firma | Proveedor de firma | Paquete 5.1 | Fin de semana 4 | Pendiente |
| D2 | Usuario técnico en el ERP con permiso de lectura de la cola y escritura de estado | Responsable ERP | Paquete 5.1 | Fin de semana 4 | Pendiente |
| D3 | Visto bueno del DPO al tratamiento y a los diagnósticos | DPO de Acme | Comité go/no-go | Semana 7 | Pendiente |
| D4 | Servidor o contenedor en la red del cliente para ejecutar el conector | Sistemas de Acme | Paquete 6.1 | Semana 7 | Pendiente |
