from app.models import CertificateStatus, Job, JobStatus
from app.services import job_processor


def test_full_flow_submit_track_list_download(client):
    recipients = [{"name": f"Person {i}", "email": f"p{i}@example.com"} for i in range(25)]
    resp = client.post("/api/jobs", json={
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": recipients,
    })
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert (status["status"], status["total"], status["successful"], status["failed"], status["progress"]) == (
        "COMPLETED", 25, 25, 0, 100,
    )

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]
    assert len(certs) == 25
    assert len({c["id"] for c in certs}) == 25

    for cert in certs:
        pdf = client.get(f"/api/certificates/{cert['id']}/download")
        assert pdf.status_code == 200
        assert cert["recipient"].encode() in pdf.content


def test_status_is_processing_while_certificate_is_being_generated(client, session_factory, monkeypatch):
    real = job_processor.generate_certificate
    seen = {}

    def spy(cert, job):
        reader = session_factory()
        try:
            seen["job"] = reader.get(Job, job.id).status
            seen["cert"] = reader.get(type(cert), cert.id).status
        finally:
            reader.close()
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", spy)
    job_id = client.post("/api/jobs", json={
        "title": "T", "course": "C", "date": "2026-10-07",
        "recipients": [{"name": "A", "email": "a@example.com"}],
    }).json()["job_id"]

    assert seen["job"] == JobStatus.PROCESSING.value
    assert seen["cert"] == CertificateStatus.PROCESSING.value
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == JobStatus.COMPLETED.value


def test_health_and_root(client):
    assert client.get("/health").json() == {"status": "ok"}
    root = client.get("/", follow_redirects=False)
    assert root.status_code in (302, 307)