"""Servidores HTTP falsos (http.server) que exponen los fakes en memoria para docker compose.

    python -m connector.fake_servers erp --port 8001
    python -m connector.fake_servers firma --port 8002 --fail-first 2
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .errors import PermanentError, TransientError
from .fakes import FakeErp, FakeSignature, seed_documents


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def log_message(self, fmt, *args):  # sin trazas por petición: el cuerpo lleva datos personales
        pass


def erp_handler(erp: FakeErp):
    class Handler(_Handler):
        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"ok": True})
            if url.path != "/documents":
                return self._send(404, {"error": "no encontrado"})
            q = parse_qs(url.query)
            status = q.get("status", [None])[0]
            if status is None:
                return self._send(200, {"items": list(erp.docs.values())})
            return self._send(200, {"items": erp.list(status, int(q.get("limit", ["10"])[0]))})

        def do_PATCH(self):
            m = re.fullmatch(r"/documents/([^/]+)", urlparse(self.path).path)
            doc_id = unquote(m.group(1)) if m else None
            if doc_id not in erp.docs:
                return self._send(404, {"error": "documento desconocido"})
            erp.update(doc_id, **self._body())
            return self._send(200, erp.docs[doc_id])

    return Handler


def signature_handler(sig: FakeSignature):
    class Handler(_Handler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/health":
                return self._send(200, {"ok": True})
            m = re.fullmatch(r"/envelopes/([^/]+)", path)
            if not m:
                return self._send(404, {"error": "no encontrado"})
            try:
                return self._send(200, {"id": m.group(1), "status": sig.status(unquote(m.group(1)))})
            except PermanentError as exc:
                return self._send(404, {"error": str(exc)})

        def do_POST(self):
            if urlparse(self.path).path != "/envelopes":
                return self._send(404, {"error": "no encontrado"})
            key = self.headers.get("Idempotency-Key")
            if not key:
                return self._send(400, {"error": "falta Idempotency-Key"})
            body = self._body()
            doc = {"id": body.get("document_id"), "signer_name": body.get("signer", {}).get("name", ""),
                   "signer_email": body.get("signer", {}).get("email", "")}
            try:
                return self._send(201, {"id": sig.create_envelope(doc, key)})
            except TransientError as exc:
                return self._send(503, {"error": str(exc)})
            except PermanentError as exc:
                return self._send(422, {"error": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidores falsos para la demo")
    parser.add_argument("service", choices=["erp", "firma"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--fail-first", type=int, default=2, help="solo firma: fallos 503 iniciales")
    parser.add_argument("--documents", type=int, default=5, help="solo erp: documentos de ejemplo")
    args = parser.parse_args()
    if args.service == "erp":
        handler = erp_handler(FakeErp(seed_documents(args.documents)))
    else:
        handler = signature_handler(FakeSignature(fail_first=args.fail_first))
    print(f"{args.service} escuchando en :{args.port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
