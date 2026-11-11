# Plan por fases

Plan base del caso de estudio. Las fechas son de ejemplo. El calendario vivo, con el avance real, las dependencias y los cambios de fecha, se gestiona en OpenProject; este documento y el diagrama son la línea base que se versiona con el código.

## Fases

Descubrimiento (semanas 1 y 2). Se inventarían los documentos que se firman, se revisan la API del proveedor y la forma en que exporta el ERP, y el DPO revisa el tratamiento de datos. Sale de esta fase el contrato de datos y el alcance firmado.

Diseño y construcción (semanas 3 a 5). Arquitectura en ADR, especificación con criterios de aceptación y desarrollo del conector con tests. Cada PR actualiza la WBS, el RAID y este plan si cambian.

Piloto en sandbox (semanas 6 y 7). El conector corre contra los sandbox del ERP y del proveedor con documentos anonimizados. Administración firma de punta a punta y se fuerzan fallos: proveedor caído, ERP lento, documento sin firmante.

Despliegue (semanas 8 y 9). Producción con un único tipo de documento durante una semana y después el resto. El conector arranca en `--dry-run` el primer día para comparar lo que enviaría con lo que administración espera.

Cierre (semana 10). Lecciones aprendidas y traspaso a soporte.

## Hitos

| Hito | Semana | Criterio |
|------|--------|----------|
| H1 Alcance firmado | 2 | Contrato de datos y alcance aprobados por Acme |
| H2 Conector listo para piloto | 5 | Tests en verde y revisión de código cerrada |
| H3 Go/no-go | 7 | Ver criterios de paso |
| H4 Primer tipo en producción | 8 | Una semana sin incidencias abiertas de severidad alta |
| H5 Todos los tipos en producción | 9 | Runbook entregado y formación hecha |

## Criterios de paso del piloto a producción

- Ningún sobre duplicado en las pruebas de caída.
- Los diagnósticos del piloto revisados sin datos personales.
- Todos los documentos del piloto en `signed`, `declined` o `error` con motivo; ninguno perdido en `sent` más de 24 horas sin explicación.
- Visto bueno del DPO (D3) y servidor de producción disponible (D4).
- Riesgos de impacto alto del RAID mitigados o aceptados por escrito.

## Diagrama de Gantt

```mermaid
gantt
    title Conector ERP y firma electrónica (línea base, fechas de ejemplo)
    dateFormat YYYY-MM-DD
    axisFormat %d/%m

    section Descubrimiento
    Inventario y contrato de datos   :d1, 2027-01-11, 10d
    Revisión DPO                      :d2, 2027-01-14, 7d
    H1 Alcance firmado               :milestone, h1, after d1, 0d

    section Diseño y construcción
    ADR y especificación              :c1, after d1, 4d
    Desarrollo y tests                :c2, after c1, 11d
    H2 Listo para piloto             :milestone, h2, after c2, 0d

    section Piloto en sandbox
    Entornos sandbox                  :p1, after c2, 2d
    Pruebas con administración        :p2, after p1, 6d
    Pruebas de fallo                  :p3, after p1, 3d
    H3 Go/no-go                      :milestone, h3, after p2, 0d

    section Despliegue
    Primer tipo de documento          :r1, after p2, 5d
    Resto de tipos y formación        :r2, after r1, 5d
    H5 Todo en producción            :milestone, h5, after r2, 0d

    section Cierre
    Lecciones y traspaso              :x1, after r2, 3d
```
