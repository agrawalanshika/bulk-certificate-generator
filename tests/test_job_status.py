from datetime import date

from app.models import Job, JobStatus
from app.services import job_processor


def payload(n=3, names=None):
    names = names or [f"Person {i}" for i in range(n)]
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [{"name": nm, "email": f"p{i}@example.com"} for i, nm in enumerate(names)],
    }


def test_status_of_completed_job(client):
    job_id = client.post("/api/jobs", json=payload(4)).json()["job_id"]
    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["status"] == JobStatus.COMPLETED.value
    assert body["total"] == 4
    assert body["successful"] == 4
    assert body["failed"] == 0
    assert body["progress"] == 100
    assert body["completed_at"] is not None


def test_status_with_partial_failures(client, monkeypatch):
    real = job_processor.generate_certificate

    def flaky(cert, job):
        if cert.recipient_name == "Bad":
            raise RuntimeError("boom")
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky)
    job_id = client.post("/api/jobs", json=payload(names=["A", "Bad", "C"])).json()["job_id"]

    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["status"] == JobStatus.COMPLETED_WITH_ERRORS.value
    assert body["successful"] == 2
    assert body["failed"] == 1
    assert body["progress"] == 100


def test_progress_while_processing(client, db_session):
    job = Job(
        title="T", course="C", issue_date=date(2026, 10, 7),
        status=JobStatus.PROCESSING.value,
        total_recipients=4, successful_count=1, failed_count=1,
    )
    db_session.add(job)
    db_session.commit()

    body = client.get(f"/api/jobs/{job.id}").json()
    assert body["status"] == JobStatus.PROCESSING.value
    assert body["progress"] == 50
    assert body["completed_at"] is None


def test_progress_is_zero_for_pending_job(client, db_session):
    job = Job(title="T", course="C", issue_date=date(2026, 10, 7), total_recipients=5)
    db_session.add(job)
    db_session.commit()
    body = client.get(f"/api/jobs/{job.id}").json()
    assert body["status"] == JobStatus.PENDING.value
    assert body["progress"] == 0


def test_invalid_job_id_returns_404(client):
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]