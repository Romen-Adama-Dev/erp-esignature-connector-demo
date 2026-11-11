# Cómo contribuir

1. Abre una rama desde `main` con el formato `tipo/descripcion-corta`, por ejemplo `fix/reintento-429`.
2. Haz el cambio con sus tests. Los tests no usan red; los fakes de `src/connector/fakes.py` cubren el ERP y el proveedor de firma.
3. Actualiza `docs/` si el cambio lo pide: WBS, RAID, plan o un ADR nuevo. Las reglas completas están en [AGENTS.md](AGENTS.md).
4. Ejecuta `uv run --with pytest pytest` y comprueba que no queda ningún dato real en el diff.
5. Un commit por PR con [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`...) y una descripción que explique qué cambia y cómo se ha probado.

Los datos de ejemplo son siempre ficticios. Si un caso necesita una persona o una empresa, usa Acme Corp y un correo `@example.com`.
