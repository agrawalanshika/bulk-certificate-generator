import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Certificate, CertificateStatus, Job, JobStatus


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_create_job_with_certificates(db):
    job = Job(total_recipients=2)
    job.certificates = [
        Certificate(recipient_name="Anshika Agrawal", recipient_email="anshika@example.com"),
        Certificate(recipient_name="Rahul Sharma", recipient_email="rahul@example.com"),
    ]
    db.add(job)
    db.commit()

    saved = db.get(Job, job.id)
    assert saved.status == JobStatus.PENDING.value
    assert saved.successful_count == 0 and saved.failed_count == 0
    assert saved.completed_at is None
    assert len(saved.certificates) == 2
    assert all(c.status == CertificateStatus.PENDING.value for c in saved.certificates)
    assert all(c.job_id == saved.id for c in saved.certificates)
    assert saved.certificates[0].file_path is None


def test_certificate_update(db):
    job = Job(total_recipients=1)
    job.certificates = [Certificate(recipient_name="A", recipient_email="a@example.com")]
    db.add(job)
    db.commit()

    cert = job.certificates[0]
    cert.status = CertificateStatus.FAILED.value
    cert.error_message = "boom"
    db.commit()

    assert db.get(Certificate, cert.id).error_message == "boom"