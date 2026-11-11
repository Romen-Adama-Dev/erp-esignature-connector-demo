"""Lógica del conector: lotes acotados, reintentos con espera exponencial y escritura de vuelta."""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .diagnostics import Diagnostics, sanitize
from .errors import PermanentError, TransientError

log = logging.getLogger("connector")


class Erp(Protocol):
    def list(self, status: str, limit: int) -> list[dict]: ...
    def update(self, doc_id: str, **fields) -> None: ...


class Signer(Protocol):
    def create_envelope(self, doc: dict, idempotency_key: str) -> str: ...
    def status(self, envelope_id: str) -> str: ...


@dataclass
class Settings:
    batch_size: int = 10
    max_batches: int = 5
    max_attempts: int = 4
    backoff_base: float = 1.0
    backoff_cap: float = 30.0
    dry_run: bool = False


@dataclass
class Summary:
    sent: int = 0
    signed: int = 0
    declined: int = 0
    failed: int = 0
    would_send: list[str] = field(default_factory=list)


def idempotency_key(doc: dict) -> str:
    """La misma versión del mismo documento produce siempre la misma clave."""
    raw = f"{doc['id']}:{doc['content_sha256']}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def backoff_delay(attempt: int, base: float, cap: float) -> float:
    """Espera tras el intento `attempt` (1, 2, 3...): base, 2*base, 4*base... con tope."""
    return min(cap, base * 2 ** (attempt - 1))


class Connector:
    def __init__(
        self,
        erp: Erp,
        signer: Signer,
        settings: Settings,
        diagnostics: Diagnostics | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.erp = erp
        self.signer = signer
        self.settings = settings
        self.diagnostics = diagnostics or Diagnostics(None)
        self.sleep = sleep

    def run(self) -> Summary:
        summary = Summary()
        if self.settings.dry_run:
            # En simulación nada cambia de estado, así que se mira un único lote.
            for doc in self.erp.list("pending", self.settings.batch_size):
                summary.would_send.append(doc["id"])
                log.info("[dry-run] enviaría %s (clave %s)", doc["id"], idempotency_key(doc))
            return summary

        for _ in range(self.settings.max_batches):
            batch = self.erp.list("pending", self.settings.batch_size)
            if not batch:
                break
            for doc in batch:
                self._dispatch(doc, summary)
        self._sync_signed(summary)
        return summary

    def _dispatch(self, doc: dict, summary: Summary) -> None:
        key = idempotency_key(doc)
        try:
            envelope_id = self._with_retry(doc, lambda: self.signer.create_envelope(doc, key))
        except (TransientError, PermanentError) as exc:
            reason = "reintentos agotados" if isinstance(exc, TransientError) else "rechazado"
            detail = sanitize(str(exc), known=(doc.get("signer_name", ""),))
            self.erp.update(doc["id"], status="error", error=f"{reason}: {detail}")
            summary.failed += 1
            log.warning("%s queda en error (%s)", doc["id"], reason)
            return
        self.erp.update(doc["id"], status="sent", envelope_id=envelope_id, idempotency_key=key)
        summary.sent += 1
        log.info("%s enviado como %s", doc["id"], envelope_id)

    def _sync_signed(self, summary: Summary) -> None:
        for doc in self.erp.list("sent", self.settings.batch_size * self.settings.max_batches):
            try:
                state = self._with_retry(doc, lambda: self.signer.status(doc["envelope_id"]))
            except (TransientError, PermanentError):
                continue  # se vuelve a consultar en la siguiente ejecución
            if state in ("signed", "declined"):
                self.erp.update(doc["id"], status=state)
                setattr(summary, state, getattr(summary, state) + 1)
                log.info("%s pasa a %s en el ERP", doc["id"], state)

    def _with_retry(self, doc: dict, call: Callable[[], str]) -> str:
        attempts = self.settings.max_attempts
        for attempt in range(1, attempts + 1):
            try:
                return call()
            except PermanentError as exc:
                self.diagnostics.record(doc, attempt, exc)
                raise
            except TransientError as exc:
                self.diagnostics.record(doc, attempt, exc)
                if attempt == attempts:
                    raise
                self.sleep(backoff_delay(attempt, self.settings.backoff_base, self.settings.backoff_cap))
        raise AssertionError("max_attempts debe ser >= 1")
