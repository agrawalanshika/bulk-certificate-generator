import logging

from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.models.job import utcnow
from app.services.certificate_generator import generate_certificate

logger = logging.getLogger(__name__)


def process_job(job_id: str, session_factory=None) -> None:
    """Generate every certificate of a job. Runs in the background.

    Uses its own DB session (the request session is closed by then) and commits
    after each certificate so progress is visible while the job is running.
    """
    factory = session_factory or SessionLocal
    db = factory()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Job %s not found; nothing to process", job_id)
            return

        job.status = JobStatus.PROCESSING.value
        db.commit()
        logger.info("Job %s processing started (%d certificates)", job_id, job.total_recipients)

        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .order_by(Certificate.created_at, Certificate.id)
            .all()
        )

        for cert in certificates:
            cert.status = CertificateStatus.PROCESSING.value
            db.commit()
            try:
                cert.file_path = generate_certificate(cert, job)
                cert.status = CertificateStatus.SUCCESS.value
                job.successful_count += 1
            except Exception as exc:  # isolate failure to this certificate
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = str(exc)
                job.failed_count += 1
                logger.error("Certificate %s failed: %s", cert.id, exc)
            db.commit()

        job.status = (
            JobStatus.COMPLETED_WITH_ERRORS.value
            if job.failed_count > 0
            else JobStatus.COMPLETED.value
        )
        job.completed_at = utcnow()
        db.commit()
        logger.info(
            "Job %s finished: %s (%d ok, %d failed)",
            job_id, job.status, job.successful_count, job.failed_count,
        )
    finally:
        db.close()