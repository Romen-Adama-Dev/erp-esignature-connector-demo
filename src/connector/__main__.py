"""CLI: python -m connector run [--dry-run]

Con ERP_URL y SIGN_URL definidas habla con esos servicios por HTTP. Sin ellas usa los fakes en
memoria, lo que permite probar el flujo sin levantar nada.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from .diagnostics import Diagnostics, SanitizingFilter
from .errors import ConnectorError
from .fakes import FakeErp, FakeSignature, seed_documents
from .http_clients import HttpErp, HttpSignature
from .processor import Connector, Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="connector")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="procesa la cola de documentos para firmar")
    run.add_argument("--dry-run", action="store_true", help="muestra qué se enviaría sin enviar nada")
    run.add_argument("--batch-size", type=int, default=int(os.getenv("BATCH_SIZE", 10)))
    run.add_argument("--max-batches", type=int, default=int(os.getenv("MAX_BATCHES", 5)))
    run.add_argument("--max-attempts", type=int, default=int(os.getenv("MAX_ATTEMPTS", 4)))
    run.add_argument("--backoff-base", type=float, default=float(os.getenv("BACKOFF_BASE", 1.0)))
    run.add_argument("--diagnostics", type=Path,
                     default=Path(os.getenv("DIAGNOSTICS_PATH", "diagnostics/diagnostics.jsonl")))
    args = parser.parse_args(argv)

    handler = logging.StreamHandler()
    handler.addFilter(SanitizingFilter())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[handler])

    erp_url, sign_url = os.getenv("ERP_URL"), os.getenv("SIGN_URL")
    if erp_url and sign_url:
        erp, signer = HttpErp(erp_url), HttpSignature(sign_url)
    else:
        logging.info("ERP_URL/SIGN_URL sin definir: se usan los fakes en memoria")
        erp, signer = FakeErp(seed_documents()), FakeSignature(fail_first=2)

    settings = Settings(batch_size=args.batch_size, max_batches=args.max_batches,
                        max_attempts=args.max_attempts, backoff_base=args.backoff_base,
                        dry_run=args.dry_run)
    diagnostics = Diagnostics(None if args.dry_run else args.diagnostics)
    try:
        summary = Connector(erp, signer, settings, diagnostics).run()
    except ConnectorError as exc:
        logging.error("ejecución abortada: %s", exc)
        return 1

    if args.dry_run:
        print(f"dry-run: {len(summary.would_send)} documentos se enviarían: {', '.join(summary.would_send)}")
    else:
        print(f"enviados={summary.sent} firmados={summary.signed} rechazados={summary.declined} "
              f"en_error={summary.failed} incidencias={len(diagnostics.records)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
