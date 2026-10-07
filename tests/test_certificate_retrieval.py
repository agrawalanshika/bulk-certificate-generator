import os

from app.models import Certificate
from app.services import job_processor


def payload(names):
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [{"name": n, "email": f"p{i}@example.com"} for i, n in enumerate(names)],
    }


def test_list_certificates(client):
    job_id = client.post("/api/jobs", json=payload(["Anshika", "Rahul"])).json()["job_id"]
    resp = client.get(f"/api/jobs/{job_id}/certificates")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert [c["recipient"] for c in body["certificates"]] == ["Anshika", "Rahul"]
    assert all(c["status"] == "SUCCESS" for c in body["certificates"])
    assert all(c["error"] is None for c in body["certificates"])


def test_list_certificates_shows_failure_error(client, monkeypatch):
    real = job_processor.generate_certificate

    def flaky(cert, job):
        if cert.recipient_name == "Bad":
            raise RuntimeError("render failed")
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky)
    job_id = client.post("/api/jobs", json=payload(["Good", "Bad"])).json()["job_id"]

    certs = {c["recipient"]: c for c in client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]}
    assert certs["Good"]["status"] == "SUCCESS"
    assert certs["Bad"]["status"] == "FAILED"
    assert certs["Bad"]["error"] == "render failed"


def test_list_certificates_invalid_job_returns_404(client):
    assert client.get("/api/jobs/nope/certificates").status_code == 404


def test_download_certificate_returns_pdf(client):
    job_id = client.post("/api/jobs", json=payload(["Anshika"])).json()["job_id"]
    cert_id = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"][0]["id"]

    resp = client.get(f"/api/certificates/{cert_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert b"Anshika" in resp.content


def test_download_invalid_certificate_returns_404(client):
    assert client.get("/api/certificates/nope/download").status_code == 404


def test_download_failed_certificate_returns_409(client, monkeypatch):
    def always_fail(cert, job):
        raise RuntimeError("boom")

    monkeypatch.setattr(job_processor, "generate_certificate", always_fail)
    job_id = client.post("/api/jobs", json=payload(["Bad"])).json()["job_id"]
    cert_id = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"][0]["id"]

    resp = client.get(f"/api/certificates/{cert_id}/download")
    assert resp.status_code == 409
    assert "FAILED" in resp.json()["detail"]


def test_download_when_file_missing_returns_404(client, db_session):
    job_id = client.post("/api/jobs", json=payload(["Anshika"])).json()["job_id"]
    cert = db_session.query(Certificate).filter_by(job_id=job_id).one()
    os.remove(cert.file_path)

    assert client.get(f"/api/certificates/{cert.id}/download").status_code == 404