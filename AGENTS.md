# Instrucciones para agentes

Este repositorio es un caso de estudio. Las personas y los agentes de IA que contribuyan siguen estas reglas, en este orden.

1. Toda contribución mantiene al día la gestión del proyecto. Si un cambio añade, quita o mueve trabajo, actualiza `docs/wbs.md`. Si crea o cierra un riesgo, supuesto, incidencia o dependencia, actualiza `docs/raid.md`. Si cambia una fecha, una fase o un hito, actualiza `docs/plan.md`. Si toma una decisión de arquitectura, añade un ADR en `docs/decisiones.md`. Todo va en la misma PR que el código. Una PR que no toca nada de esto explica en la descripción por qué no hace falta.
2. Solo datos ficticios: Acme Corp, personas inventadas y dominios `example.com`. Nada de clientes, bancos o empresas reales, ni claves o tokens, ni siquiera de sandbox.
3. Los tests no hacen llamadas de red. Se usan los fakes de `src/connector/fakes.py`.
4. Ningún log ni diagnóstico guarda datos personales. Cualquier campo nuevo en `Diagnostics` pasa por `sanitize()` y tiene un test.
5. Solo biblioteca estándar en `src/`. Una dependencia nueva necesita un ADR.
6. Una tarea, una rama (`tipo/descripcion-corta`) y una PR con Conventional Commits. No se fusiona sin revisión de Romén.
7. Antes de abrir la PR: `uv run --with pytest pytest` en verde.

La prosa del repositorio está en español, con el resumen en inglés al principio del README.
