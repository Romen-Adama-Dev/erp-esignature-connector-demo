"""Saneado de textos y registro de diagnósticos sin datos personales."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){4,7}\b"), "<iban>"),
    (re.compile(r"\b[XYZ]?\d{7,8}[A-Z]\b"), "<dni>"),
    (re.compile(r"(?<!\w)\+?\d(?:[ -]?\d){8,13}(?!\w)"), "<telefono>"),
]


def sanitize(text: str, known: tuple[str, ...] = ()) -> str:
    """Sustituye correos, IBAN, DNI/NIE, teléfonos y los valores de `known` (p. ej. nombres)."""
    for value in known:
        if value:
            text = text.replace(value, "<dato-personal>")
    for pattern, mark in _PATTERNS:
        text = pattern.sub(mark, text)
    return text


class SanitizingFilter(logging.Filter):
    """Filtro de logging que sanea el mensaje ya formateado antes de emitirlo."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(record.getMessage())
        record.args = None
        return True


class Diagnostics:
    """Guarda una línea JSON por incidencia. Solo campos fijos y el mensaje saneado."""

    def __init__(self, path: Path | None):
        self.path = path
        self.records: list[dict] = []

    def record(self, doc: dict, attempt: int, error: Exception) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "document_id": doc["id"],
            "attempt": attempt,
            "error": type(error).__name__,
            "message": sanitize(str(error), known=(doc.get("signer_name", ""),)),
        }
        self.records.append(entry)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
