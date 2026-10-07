import logging
import os
from datetime import date

import pytest

from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.services import certificate_generator, job_processor
from app.services.certificate_generator import generate_certificate


def payload(names):
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [{"name": n, "email": f"p{i}@example.com"} for i, n in enumerate(names)],
    }


def fail_for(names, monkeypatch, message="render failed"):
    real = job_processor.generate_certificate

    def flaky(cert, job):
        if cert.recipient_name in names:
            raise RuntimeError(message)
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky)


def test_failures_anywhere_do_not_stop_valid_certificates(client, db_session, monkeypatch):
    names = ["Bad1", "Ok1", "Ok2", "Bad2", "Ok3", "Bad3"]
    fail_for({"Bad1", "Bad2", "Bad3"}, monkeypatch)

    job_id = client.post("/api/jobs", json=payload(names)).json()["job_id"]

    job = db_session.get(Job, job_id)
    assert job.status == JobStatus.COMPLETED_WITH_ERRORS.value
    assert job.successful_count == 3 and job.failed_count == 3
    for cert in job.certificates:
        if cert.recipient_name.startswith("Ok"):
            assert cert.status == CertificateStatus.SUCCESS.value
            assert os.path.exists(cert.file_path)
        else:
            assert cert.status == CertificateStatus.FAILED.value
            assert cert.error_message == "render failed"
            assert cert.file_path is None


def test_all_failures_mark_job_failed(client, db_session, monkeypatch):
    fail_for({"A", "B"}, monkeypatch)
    job_id = client.post("/api/jobs", json=payload(["A", "B"])).json()["job_id"]

    job = db_session.get(Job, job_id)
    assert job.status == JobStatus.FAILED.value
    assert job.successful_count == 0 and job.failed_count == 2
    assert job.completed_at is not None


def test_error_message_is_never_empty(client, db_session, monkeypatch):
    def silent_fail(cert, job):
        raise ValueError()

    monkeypatch.setattr(job_processor, "generate_certificate", silent_fail)
    job_id = client.post("/api/jobs", json=payload(["A"])).json()["job_id"]
    cert = db_session.query(Certificate).filter_by(job_id=job_id).one()
    assert cert.error_message == "ValueError"


def test_unexpected_processor_error_marks_job_failed(client, db_session, monkeypatch):
    real = job_processor._process_certificate
    calls = {"n": 0}

    def explode_on_second(db, job, cert):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("db exploded")
        return real(db, job, cert)

    monkeypatch.setattr(job_processor, "_process_certificate", explode_on_second)
    job_id = client.post("/api/jobs", json=payload(["A", "B", "C"])).json()["job_id"]

    job = db_session.get(Job, job_id)
    assert job.status == JobStatus.FAILED.value
    assert job.completed_at is not None
    assert job.successful_count == 1
    assert job.failed_count == 2
    by_name = {c.recipient_name: c for c in job.certificates}
    assert by_name["A"].status == CertificateStatus.SUCCESS.value
    for name in ("B", "C"):
        assert by_name[name].status == CertificateStatus.FAILED.value
        assert "Job aborted" in by_name[name].error_message
        assert "db exploded" in by_name[name].error_message


def test_partial_pdf_is_removed_when_rendering_fails(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("draw failed")

    monkeypatch.setattr(certificate_generator, "_draw_template", broken)
    job = Job(id="j1", title="T", course="C", issue_date=date(2026, 10, 7))
    cert = Certificate(id="c1", job_id="j1", recipient_name="A", recipient_email="a@example.com")

    with pytest.raises(RuntimeError, match="draw failed"):
        generate_certificate(cert, job, output_dir=str(tmp_path))
    assert not (tmp_path / "job_j1" / "certificate_c1.pdf").exists()


def test_lifecycle_is_logged(client, monkeypatch, caplog):
    fail_for({"Bad"}, monkeypatch)
    with caplog.at_level(logging.INFO):
        job_id = client.post("/api/jobs", json=payload(["Good", "Bad"])).json()["job_id"]

    text = caplog.text
    assert f"Job {job_id} created" in text
    assert "Generating certificate for Good" in text
    assert "Certificate generation failed for Bad" in text
    assert f"Job {job_id} completed: COMPLETED_WITH_ERRORS" in text