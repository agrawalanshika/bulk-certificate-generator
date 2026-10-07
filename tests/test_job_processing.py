import os
from datetime import date

from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.services import job_processor
from app.services.job_processor import process_job


def payload(names):
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [
            {"name": n, "email": f"user{i}@example.com"} for i, n in enumerate(names)
        ],
    }


def test_post_returns_pending_then_job_completes_in_background(client, db_session):
    resp = client.post("/api/jobs", json=payload(["Anshika", "Rahul", "Priya"]))
    assert resp.status_code == 201
    assert resp.json()["status"] == JobStatus.PENDING.value  # response is immediate

    job = db_session.get(Job, resp.json()["job_id"])
    assert job.status == JobStatus.COMPLETED.value
    assert job.successful_count == 3
    assert job.failed_count == 0
    assert job.completed_at is not None
    assert len(job.certificates) == 3
    for cert in job.certificates:
        assert cert.status == CertificateStatus.SUCCESS.value
        assert cert.file_path and os.path.exists(cert.file_path)


def test_process_job_directly(session_factory, generated_dir):
    db = session_factory()
    job = Job(title="T", course="C", issue_date=date(2026, 10, 7), total_recipients=2)
    job.certificates = [
        Certificate(recipient_name="A", recipient_email="a@example.com"),
        Certificate(recipient_name="B", recipient_email="b@example.com"),
    ]
    db.add(job)
    db.commit()
    job_id = job.id

    process_job(job_id, session_factory=session_factory)

    db.expire_all()
    job = db.get(Job, job_id)
    assert job.status == JobStatus.COMPLETED.value
    assert job.successful_count == 2
    db.close()


def test_one_failure_does_not_stop_others(client, db_session, monkeypatch):
    real = job_processor.generate_certificate

    def flaky(cert, job):
        if cert.recipient_name == "Bad Apple":
            raise RuntimeError("render failed")
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky)

    job_id = client.post("/api/jobs", json=payload(["Good One", "Bad Apple", "Good Two"])).json()["job_id"]

    job = db_session.get(Job, job_id)
    assert job.status == JobStatus.COMPLETED_WITH_ERRORS.value
    assert job.successful_count == 2
    assert job.failed_count == 1
    by_name = {c.recipient_name: c for c in job.certificates}
    assert by_name["Bad Apple"].status == CertificateStatus.FAILED.value
    assert by_name["Bad Apple"].error_message == "render failed"
    assert by_name["Good One"].status == CertificateStatus.SUCCESS.value
    assert by_name["Good Two"].status == CertificateStatus.SUCCESS.value


def test_process_unknown_job_does_not_crash(session_factory):
    process_job("does-not-exist", session_factory=session_factory)