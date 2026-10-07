from datetime import date

from app.models import Certificate, CertificateStatus, Job
from app.services import job_processor


def payload(names):
    return {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [{"name": n, "email": f"p{i}@example.com"} for i, n in enumerate(names)],
    }


def cert_ids(client, job_id):
    return [c["id"] for c in client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]]


def test_download_has_pdf_headers(client):
    job_id = client.post("/api/jobs", json=payload(["Anshika"])).json()["job_id"]
    cert_id = cert_ids(client, job_id)[0]

    resp = client.get(f"/api/certificates/{cert_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert f"certificate_{cert_id}.pdf" in resp.headers["content-disposition"]


def test_each_certificate_downloads_its_own_pdf(client):
    job_id = client.post("/api/jobs", json=payload(["Alice", "Bob"])).json()["job_id"]
    alice_id, bob_id = cert_ids(client, job_id)

    alice = client.get(f"/api/certificates/{alice_id}/download").content
    bob = client.get(f"/api/certificates/{bob_id}/download").content
    assert b"Alice" in alice and b"Bob" not in alice
    assert b"Bob" in bob and b"Alice" not in bob


def test_download_can_be_repeated(client):
    job_id = client.post("/api/jobs", json=payload(["Anshika"])).json()["job_id"]
    cert_id = cert_ids(client, job_id)[0]
    first = client.get(f"/api/certificates/{cert_id}/download").content
    second = client.get(f"/api/certificates/{cert_id}/download").content
    assert first == second


def test_download_failed_certificate_is_409_but_others_download(client, monkeypatch):
    real = job_processor.generate_certificate

    def flaky(cert, job):
        if cert.recipient_name == "Bad":
            raise RuntimeError("boom")
        return real(cert, job)

    monkeypatch.setattr(job_processor, "generate_certificate", flaky)
    job_id = client.post("/api/jobs", json=payload(["Good", "Bad"])).json()["job_id"]
    good_id, bad_id = cert_ids(client, job_id)

    assert client.get(f"/api/certificates/{good_id}/download").status_code == 200
    assert client.get(f"/api/certificates/{bad_id}/download").status_code == 409


def test_download_not_ready_certificates_return_409(client, db_session):
    job = Job(title="T", course="C", issue_date=date(2026, 10, 7), total_recipients=2)
    job.certificates = [
        Certificate(recipient_name="P", recipient_email="p@example.com",
                    status=CertificateStatus.PENDING.value),
        Certificate(recipient_name="Q", recipient_email="q@example.com",
                    status=CertificateStatus.PROCESSING.value),
    ]
    db_session.add(job)
    db_session.commit()

    for cert in job.certificates:
        resp = client.get(f"/api/certificates/{cert.id}/download")
        assert resp.status_code == 409
        assert cert.status in resp.json()["detail"]


def test_download_unknown_certificate_returns_404(client):
    resp = client.get("/api/certificates/unknown/download")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]