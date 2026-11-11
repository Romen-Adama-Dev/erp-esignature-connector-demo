# Estructura de desglose del trabajo (WBS)

Caso de estudio: integración del ERP de Acme Corp con una plataforma de firma electrónica. Los paquetes de trabajo están pensados para un equipo pequeño: un PM técnico, una persona de desarrollo, el responsable del ERP en el cliente y usuarios clave de administración. Las estimaciones están en jornadas y son de planificación, no medidas.

| ID | Paquete de trabajo | Entregable | Responsable | Estimación (jornadas) |
|----|--------------------|------------|-------------|-----------------------|
| 1 | Gestión del proyecto | | PM técnico | 4 |
| 1.1 | Acta de constitución y alcance | Alcance firmado por Acme | PM técnico | 1 |
| 1.2 | Plan, RAID y seguimiento semanal | `plan.md`, `raid.md` al día | PM técnico | 2 |
| 1.3 | Comités de paso entre fases | Actas de go/no-go | PM técnico | 1 |
| 2 | Descubrimiento | | PM técnico | 5 |
| 2.1 | Inventario de documentos que se firman | Lista de tipos, volúmenes y firmantes | Usuarios clave | 1,5 |
| 2.2 | Revisión de la API de firma (límites, errores, idempotencia) | Nota técnica | Desarrollo | 1 |
| 2.3 | Cómo exporta el ERP (cola, campos, estados) | Contrato de datos ERP | Responsable ERP | 1,5 |
| 2.4 | Análisis de protección de datos | Registro de tratamiento revisado por el DPO | PM técnico | 1 |
| 3 | Diseño | | PM técnico | 3 |
| 3.1 | Arquitectura y flujo de estados | ADR-001 a ADR-006 | PM técnico | 1,5 |
| 3.2 | Especificación del conector | Criterios de aceptación por caso | PM técnico | 1 |
| 3.3 | Diseño de diagnósticos sin datos personales | Lista de campos permitidos | PM técnico | 0,5 |
| 4 | Construcción | | Desarrollo | 7 |
| 4.1 | Lectura de la cola por lotes | `processor.py` con tests | Desarrollo | 1,5 |
| 4.2 | Envío con reintentos e idempotencia | Tests de reintento e idempotencia | Desarrollo | 2 |
| 4.3 | Escritura de vuelta en el ERP | Tests de estados | Desarrollo | 1,5 |
| 4.4 | Saneado de logs y diagnósticos | Tests de saneado | Desarrollo | 1 |
| 4.5 | Empaquetado (Docker, CLI, dry-run) | Imagen y `compose.yaml` | Desarrollo | 1 |
| 5 | Piloto en sandbox | | PM técnico | 6 |
| 5.1 | Entornos sandbox de ERP y firma | Credenciales de sandbox en el gestor de secretos | Responsable ERP | 1 |
| 5.2 | Pruebas con documentos reales anonimizados | Informe de piloto | Usuarios clave | 3 |
| 5.3 | Pruebas de fallo (caída del proveedor, ERP lento) | Resultados por escenario | Desarrollo | 1 |
| 5.4 | Comité go/no-go | Acta con decisión | PM técnico | 1 |
| 6 | Despliegue | | PM técnico | 4 |
| 6.1 | Despliegue en producción con un tipo de documento | Conector en producción | PM técnico | 1 |
| 6.2 | Ampliación al resto de tipos | Todos los tipos activos | Desarrollo | 1,5 |
| 6.3 | Guía de operación y formación | Runbook y sesión con administración | PM técnico | 1,5 |
| 7 | Cierre | | PM técnico | 1 |
| 7.1 | Lecciones aprendidas y traspaso a soporte | Documento de cierre | PM técnico | 1 |

Total estimado: 30 jornadas.

## Diccionario de los paquetes con más riesgo

4.2 Envío con reintentos e idempotencia. Está terminado cuando un reenvío tras una caída no crea un segundo sobre, cuando un error 4xx no se reintenta y cuando el número de llamadas por documento nunca supera `max_attempts`. Los tests de `tests/test_connector.py` cubren los tres casos.

5.2 Pruebas con documentos reales anonimizados. Está terminado cuando administración ha firmado en sandbox al menos un documento de cada tipo y el informe recoge los rechazos y su causa.
