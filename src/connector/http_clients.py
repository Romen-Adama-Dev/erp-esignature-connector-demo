"""Clientes HTTP con urllib para el ERP y el proveedor de firma."""

import json
import urllib.error
import urllib.parse
import urllib.request

from .errors import PermanentError, TransientError


def _request(method: str, url: str, body: dict | None = None, headers: dict | None = None,
             timeout: float = 10) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        if exc.code == 429 or exc.code >= 500:
            raise TransientError(f"HTTP {exc.code}: {detail}") from exc
        raise PermanentError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TransientError(f"conexión fallida: {getattr(exc, 'reason', exc)}") from exc
    return json.loads(raw) if raw else {}


class HttpErp:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def list(self, status: str, limit: int) -> list[dict]:
        query = urllib.parse.urlencode({"status": status, "limit": limit})
        return _request("GET", f"{self.base_url}/documents?{query}")["items"]

    def update(self, doc_id: str, **fields) -> None:
        _request("PATCH", f"{self.base_url}/documents/{urllib.parse.quote(doc_id)}", fields)


class HttpSignature:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def create_envelope(self, doc: dict, idempotency_key: str) -> str:
        body = {
            "document_id": doc["id"],
            "title": doc["title"],
            "content_sha256": doc["content_sha256"],
            "signer": {"name": doc["signer_name"], "email": doc["signer_email"]},
        }
        resp = _request("POST", f"{self.base_url}/envelopes", body,
                        headers={"Idempotency-Key": idempotency_key})
        return resp["id"]

    def status(self, envelope_id: str) -> str:
        return _request("GET", f"{self.base_url}/envelopes/{urllib.parse.quote(envelope_id)}")["status"]
