from datetime import date

from app.models import Certificate, CertificateStatus, Job, JobStatus


def payload(n=2):
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [
            {"name": f"Person {i}", "email": f"person{i}@example.com"} for i in range(n)
        ],
    }


def test_create_job_returns_201_and_job_id(client):
    resp = client.post("/api/jobs", json=payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == JobStatus.PENDING.value
    assert len(body["job_id"]) == 32


def test_create_job_persists_job_and_certificates(client, db_session):
    job_id = client.post("/api/jobs", json=payload(3)).json()["job_id"]

    job = db_session.get(Job, job_id)
    assert job.title == "Certificate of Completion"
    assert job.course == "AI/ML Workshop"
    assert job.issue_date == date(2026, 10, 7)
    assert job.total_recipients == 3
    assert job.successful_count == 0 and job.failed_count == 0
    assert len(job.certificates) == 3
    assert all(c.status == CertificateStatus.PENDING.value for c in job.certificates)
    assert {c.recipient_email for c in job.certificates} == {
        "person0@example.com",
        "person1@example.com",
        "person2@example.com",
    }


def test_bulk_request_with_100_recipients(client, db_session):
    resp = client.post("/api/jobs", json=payload(100))
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]
    assert db_session.query(Certificate).filter_by(job_id=job_id).count() == 100


def test_invalid_request_creates_nothing(client, db_session):
    bad = payload()
    bad["recipients"][0]["email"] = "not-an-email"
    resp = client.post("/api/jobs", json=bad)
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "recipients.0.email"
    assert db_session.query(Job).count() == 0


def test_empty_recipients_rejected(client):
    bad = payload()
    bad["recipients"] = []
    assert client.post("/api/jobs", json=bad).status_code == 422