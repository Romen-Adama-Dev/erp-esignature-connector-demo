# Decisiones de arquitectura

Formato ADR corto: contexto, decisión y consecuencias. Una decisión aceptada no se edita; si cambia, se añade otra que la sustituye.

## ADR-001 Conector por lotes ejecutado de forma programada

Estado: aceptada.

Contexto. El ERP genera documentos a lo largo del día, con picos a fin de mes. El proveedor de firma limita las peticiones por minuto.

Decisión. El conector se ejecuta de forma programada (por ejemplo, cada cinco minutos) y procesa como mucho `max_batches` lotes de `batch_size` documentos. Lo que no cabe espera a la ejecución siguiente.

Consecuencias. La carga sobre el proveedor y la duración de cada ejecución están acotadas. En un pico, un documento puede tardar algunos minutos más en salir. Ese retraso se valida con administración durante el descubrimiento.

## ADR-002 Reintentos limitados y solo para errores transitorios

Estado: aceptada.

Contexto. Los timeouts, los 429 y los 5xx suelen resolverse en segundos. Un 4xx distinto de 429 indica un dato inválido y no cambia al repetir la llamada.

Decisión. Se reintentan los errores transitorios con espera exponencial (1, 2, 4 segundos, con tope de 30) hasta `max_attempts`, 4 por defecto. Los permanentes no se reintentan. Al agotar los intentos, el documento pasa a `error` en el ERP con el motivo saneado y no vuelve a la cola sin intervención de una persona.

Consecuencias. Una caída larga del proveedor deja documentos en `error` en lugar de reintentos indefinidos que alargarían cada ejecución y esconderían el problema. El coste es trabajo manual para devolverlos a `pending`. Si el piloto muestra que pasa a menudo, la opción prevista es un reintento diferido con una cola aparte. Subir `max_attempts` solo alargaría cada ejecución.

## ADR-003 Clave de idempotencia derivada del documento

Estado: aceptada.

Contexto. El envío al proveedor y la escritura en el ERP no son atómicos. Si el conector cae entre los dos, el documento sigue en `pending` aunque el sobre exista.

Decisión. Cada envío lleva `Idempotency-Key = sha256(id + ":" + hash del contenido)` truncado a 32 caracteres. El proveedor devuelve el sobre existente si la clave se repite. La clave también se guarda en el ERP junto al identificador del sobre.

Consecuencias. Un reenvío tras una caída no duplica la solicitud al firmante. Una versión nueva del documento tiene otra clave y genera otro sobre. Depende del supuesto A1 del RAID: si el proveedor no admite claves de idempotencia, habría que consultar por referencia externa antes de crear.

## ADR-004 Diagnósticos con campos fijos y mensajes saneados

Estado: aceptada.

Contexto. Los mensajes de error de un proveedor de firma suelen incluir el nombre o el correo del firmante. Los logs pueden acabar en herramientas de soporte a las que accede más gente que al ERP.

Decisión. Cada incidencia se guarda como una línea JSON con documento, intento, tipo de error y mensaje. El mensaje pasa por `sanitize()`, que enmascara correos, DNI/NIE, teléfonos, IBAN y el nombre del firmante. El handler de logging aplica el mismo filtro.

Consecuencias. El soporte puede seguir un documento por su identificador sin ver datos personales. El saneado por patrones no es exhaustivo, así que la lista de campos permitidos es la primera defensa y el filtro, la segunda.

## ADR-005 Sondeo del estado de firma en lugar de webhook

Estado: aceptada para el piloto.

Contexto. Un webhook del proveedor exigiría un endpoint accesible desde internet hacia la red donde vive el ERP.

Decisión. Tras enviar, cada ejecución consulta el estado de los documentos en `sent` y escribe `signed` o `declined` en el ERP.

Consecuencias. Hay un retraso de hasta un ciclo entre la firma y su reflejo en el ERP, y algunas llamadas extra al proveedor. Para el despliegue se puede revisar con sistemas de Acme si se expone un webhook detrás de su proxy.

## ADR-006 Solo biblioteca estándar de Python

Estado: aceptada.

Contexto. El conector se ejecuta en un servidor del cliente que mantiene su equipo de sistemas.

Decisión. Python 3.12 con `urllib`, `json`, `logging` y `http.server` para los servidores falsos. pytest solo en desarrollo.

Consecuencias. No hay dependencias que actualizar en producción. Si más adelante hace falta OAuth con renovación de tokens o reintentos más finos, se reconsidera con un ADR nuevo.
