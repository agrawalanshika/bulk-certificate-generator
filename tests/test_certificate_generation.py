from datetime import date

from app.models import Certificate, Job
from app.services.certificate_generator import generate_certificate


def make_job_and_cert(name="Anshika Agrawal"):
    job = Job(id="job123", title="Certificate of Completion", course="AI/ML Workshop",
              issue_date=date(2026, 10, 7), total_recipients=1)
    cert = Certificate(id="cert456", job_id=job.id, recipient_name=name,
                       recipient_email="anshika@example.com")
    return job, cert


def test_pdf_is_generated_in_expected_location(tmp_path):
    job, cert = make_job_and_cert()
    path = generate_certificate(cert, job, output_dir=str(tmp_path))

    assert path == str(tmp_path / "job_job123" / "certificate_cert456.pdf")
    with open(path, "rb") as f:
        data = f.read()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_pdf_contains_recipient_data(tmp_path):
    job, cert = make_job_and_cert()
    path = generate_certificate(cert, job, output_dir=str(tmp_path))
    data = open(path, "rb").read()
    assert b"Anshika Agrawal" in data
    assert b"AI/ML Workshop" in data
    assert b"07/10/2026" in data
    assert b"cert456" in data


def test_very_long_name_still_generates(tmp_path):
    job, cert = make_job_and_cert(name="A" * 200)
    path = generate_certificate(cert, job, output_dir=str(tmp_path))
    assert open(path, "rb").read().startswith(b"%PDF")


def test_each_recipient_gets_separate_file(tmp_path):
    job, cert1 = make_job_and_cert("One")
    cert2 = Certificate(id="cert789", job_id=job.id, recipient_name="Two",
                        recipient_email="two@example.com")
    p1 = generate_certificate(cert1, job, output_dir=str(tmp_path))
    p2 = generate_certificate(cert2, job, output_dir=str(tmp_path))
    assert p1 != p2