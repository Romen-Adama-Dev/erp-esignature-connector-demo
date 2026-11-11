import json
import logging

import pytest

from connector.__main__ import main
from connector.diagnostics import Diagnostics, SanitizingFilter, sanitize
from connector.errors import TransientError
from connector.fakes import FakeErp, FakeSignature, seed_documents
from connector.processor import Connector, Settings, backoff_delay, idempotency_key


def make(docs=None, signer=None, sleeps=None, diagnostics=None, **settings):
    erp = FakeErp(docs if docs is not None else seed_documents(4))
    signer = signer or FakeSignature()
    sleeps = sleeps if sleeps is not None else []
    conn = Connector(erp, signer, Settings(**settings), diagnostics, sleep=sleeps.append)
    return conn, erp, signer


# Lotes

def test_processes_queue_in_bounded_batches():
    docs = [{**d, "signer_email": d["signer_email"] or "firmas@example.com"} for d in seed_documents(25)]
    conn, erp, _ = make(docs=docs, batch_size=10, max_batches=2, signer=FakeSignature(polls_to_sign=99))
    summary = conn.run()
    assert summary.sent == 20
    assert sum(d["status"] == "pending" for d in erp.docs.values()) == 5
    assert all(limit <= 10 for status, limit in erp.list_calls if status == "pending")


def test_dry_run_sends_nothing_and_writes_nothing():
    conn, erp, signer = make(dry_run=True, batch_size=3)
    summary = conn.run()
    assert summary.would_send == ["ACME-CTR-0001", "ACME-CTR-0002", "ACME-CTR-0003"]
    assert signer.create_calls == 0
    assert all(d["status"] == "pending" for d in erp.docs.values())


# Reintentos y espera

def test_backoff_doubles_and_is_capped():
    assert [backoff_delay(n, 1.0, 5.0) for n in (1, 2, 3, 4)] == [1.0, 2.0, 4.0, 5.0]


def test_transient_errors_are_retried_with_backoff():
    sleeps = []
    conn, erp, signer = make(docs=seed_documents(1), signer=FakeSignature(fail_first=2),
                             sleeps=sleeps, max_attempts=4, backoff_base=0.5)
    summary = conn.run()
    assert summary.sent == 1 and summary.failed == 0
    assert sleeps == [0.5, 1.0]
    assert signer.create_calls == 3


def test_gives_up_after_max_attempts_and_marks_error():
    sleeps = []
    conn, erp, signer = make(docs=seed_documents(1), signer=FakeSignature(fail_first=10),
                             sleeps=sleeps, max_attempts=3)
    summary = conn.run()
    assert summary.failed == 1
    assert signer.create_calls == 3
    assert len(sleeps) == 2  # no se espera después del último intento
    assert erp.docs["ACME-CTR-0001"]["status"] == "error"
    assert erp.docs["ACME-CTR-0001"]["error"].startswith("reintentos agotados")


def test_permanent_error_is_not_retried():
    doc = seed_documents(5)[4]  # Elena Prieto Gil, sin correo
    conn, erp, signer = make(docs=[doc], max_attempts=4)
    summary = conn.run()
    assert summary.failed == 1
    assert signer.create_calls == 1
    assert erp.docs[doc["id"]]["status"] == "error"


# Idempotencia

def test_idempotency_key_is_stable_per_document_version():
    doc = seed_documents(1)[0]
    assert idempotency_key(doc) == idempotency_key(dict(doc))
    assert idempotency_key(doc) != idempotency_key({**doc, "content_sha256": "otra-version"})


def test_resend_after_crash_does_not_duplicate_envelope():
    """Si el conector cae entre el envío y la escritura en el ERP, el reenvío reutiliza el sobre."""
    docs = seed_documents(1)
    signer = FakeSignature(polls_to_sign=99)
    signer.create_envelope(docs[0], idempotency_key(docs[0]))  # envío previo sin escritura de vuelta
    conn, erp, _ = make(docs=docs, signer=signer)
    conn.run()
    assert len(signer.envelopes) == 1
    assert erp.docs["ACME-CTR-0001"]["envelope_id"] == "env-0001"


def test_second_run_does_not_resend():
    conn, erp, signer = make(signer=FakeSignature(polls_to_sign=99))
    conn.run()
    calls = signer.create_calls
    conn.run()
    assert signer.create_calls == calls


# Saneado de logs y diagnósticos

def test_sanitize_masks_personal_data():
    text = ("Fallo para Lucía Ferrer Ortega <lucia.ferrer@example.com>, DNI 12345678Z, "
            "tel +34 600 123 456, IBAN ES91 2100 0418 4502 0005 1332")
    out = sanitize(text, known=("Lucía Ferrer Ortega",))
    for leaked in ("Lucía", "lucia.ferrer", "12345678Z", "600 123 456", "ES91"):
        assert leaked not in out
    assert "<email>" in out and "<dni>" in out and "<iban>" in out and "<telefono>" in out


def test_diagnostics_file_has_no_personal_data(tmp_path):
    path = tmp_path / "diag.jsonl"
    doc = seed_documents(5)[4]
    conn, erp, _ = make(docs=[doc], diagnostics=Diagnostics(path))
    conn.run()
    content = path.read_text(encoding="utf-8")
    assert "Elena" not in content and "Prieto" not in content
    entry = json.loads(content.splitlines()[0])
    assert set(entry) == {"ts", "document_id", "attempt", "error", "message"}
    assert "Elena" not in erp.docs[doc["id"]]["error"]


def test_log_filter_sanitizes_formatted_message():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "aviso a %s", ("ana.beltran@example.com",), None)
    SanitizingFilter().filter(record)
    assert record.getMessage() == "aviso a <email>"


# Escritura de vuelta al ERP

def test_writes_signed_status_back_to_erp():
    conn, erp, _ = make(signer=FakeSignature(polls_to_sign=1))
    summary = conn.run()
    assert summary.signed == 4
    for d in erp.docs.values():
        assert d["status"] == "signed"
        assert d["envelope_id"].startswith("env-")
        assert d["idempotency_key"] == idempotency_key(d)


def test_unsigned_envelopes_stay_sent_until_next_run():
    conn, erp, _ = make(signer=FakeSignature(polls_to_sign=2))
    first = conn.run()
    assert first.sent == 4 and first.signed == 0
    assert all(d["status"] == "sent" for d in erp.docs.values())
    second = conn.run()
    assert second.signed == 4


def test_status_check_failure_leaves_document_sent():
    class FlakyStatus(FakeSignature):
        def status(self, envelope_id):
            raise TransientError("timeout")

    conn, erp, _ = make(docs=seed_documents(1), signer=FlakyStatus(), max_attempts=2)
    conn.run()
    assert erp.docs["ACME-CTR-0001"]["status"] == "sent"


# CLI

def test_cli_dry_run_uses_in_memory_fakes(monkeypatch, capsys):
    monkeypatch.delenv("ERP_URL", raising=False)
    monkeypatch.delenv("SIGN_URL", raising=False)
    assert main(["run", "--dry-run"]) == 0
    assert "5 documentos se enviarían" in capsys.readouterr().out


@pytest.mark.parametrize("attempts", [1, 2])
def test_max_attempts_bounds_calls(attempts):
    conn, _, signer = make(docs=seed_documents(1), signer=FakeSignature(fail_first=5), max_attempts=attempts)
    conn.run()
    assert signer.create_calls == attempts
