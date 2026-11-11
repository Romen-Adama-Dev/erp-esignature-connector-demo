"""ERP y proveedor de firma simulados en memoria. Los usan los tests, la CLI y los servidores falsos.

Todos los datos son ficticios: empresa Acme Corp, personas inventadas, dominios example.com.
"""

import hashlib

from .errors import PermanentError, TransientError

_PEOPLE = [
    ("Lucía Ferrer Ortega", "lucia.ferrer@example.com"),
    ("Marcos Vidal Peña", "marcos.vidal@example.com"),
    ("Ana Beltrán Ruiz", "ana.beltran@example.com"),
    ("Javier Soto Medina", "javier.soto@example.com"),
    ("Elena Prieto Gil", ""),  # sin correo: el proveedor la rechaza y el caso queda en error
]


def seed_documents(count: int = 5) -> list[dict]:
    docs = []
    for i in range(count):
        name, email = _PEOPLE[i % len(_PEOPLE)]
        number = f"ACME-CTR-{i + 1:04d}"
        docs.append({
            "id": number,
            "title": f"Contrato de suministro {number} - Acme Corp",
            "signer_name": name,
            "signer_email": email,
            "content_sha256": hashlib.sha256(number.encode()).hexdigest(),
            "status": "pending",
        })
    return docs


class FakeErp:
    """Cola de documentos para firmar. Registra cada llamada para poder comprobarla."""

    def __init__(self, docs: list[dict]):
        self.docs = {d["id"]: dict(d) for d in docs}
        self.list_calls: list[tuple[str, int]] = []

    def list(self, status: str, limit: int) -> list[dict]:
        self.list_calls.append((status, limit))
        return [dict(d) for d in self.docs.values() if d["status"] == status][:limit]

    def update(self, doc_id: str, **fields) -> None:
        self.docs[doc_id].update(fields)


class FakeSignature:
    """Proveedor de firma con fallos programables.

    fail_first: cuántas llamadas a create_envelope fallan con un error transitorio.
    polls_to_sign: cuántas consultas de estado hacen falta para que un sobre figure firmado.
    """

    def __init__(self, fail_first: int = 0, polls_to_sign: int = 1):
        self.fail_first = fail_first
        self.polls_to_sign = polls_to_sign
        self.envelopes: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}
        self.create_calls = 0

    def create_envelope(self, doc: dict, idempotency_key: str) -> str:
        self.create_calls += 1
        if self.fail_first > 0:
            self.fail_first -= 1
            raise TransientError("503 servicio no disponible")
        if idempotency_key in self.by_key:
            return self.by_key[idempotency_key]
        if not doc.get("signer_email"):
            # El mensaje lleva el nombre a propósito: los tests comprueban que no llega al log.
            raise PermanentError(f"422 firmante sin correo: {doc['signer_name']}")
        envelope_id = f"env-{len(self.envelopes) + 1:04d}"
        self.envelopes[envelope_id] = {"document_id": doc["id"], "polls": 0}
        self.by_key[idempotency_key] = envelope_id
        return envelope_id

    def status(self, envelope_id: str) -> str:
        env = self.envelopes.get(envelope_id)
        if env is None:
            raise PermanentError(f"404 sobre {envelope_id} desconocido")
        env["polls"] += 1
        return "signed" if env["polls"] >= self.polls_to_sign else "pending"
