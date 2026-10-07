import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.models.job import utcnow
from app.services.certificate_generator import generate_certificate

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 500


def _error_text(exc: Exception) -> str:
    return (str(exc) or exc.__class__.__name__)[:MAX_ERROR_LENGTH]


def _final_status(job: Job) -> str:
    """COMPLETED: all ok. FAILED: nothing could be generated. Otherwise mixed."""
    if job.failed_count == 0:
        return JobStatus.COMPLETED.value
    if job.successful_count == 0:
        return JobStatus.FAILED.value
    return JobStatus.COMPLETED_WITH_ERRORS.value


def _process_certificate(db: Session, job: Job, cert: Certificate) -> None:
    """Generate one certificate. A generation error only fails this certificate."""
    logger.info("Generating certificate for %s", cert.recipient_name)
    cert.status = CertificateStatus.PROCESSING.value
    db.commit()
    try:
        cert.file_path = generate_certificate(cert, job)
        cert.status = CertificateStatus.SUCCESS.value
        job.successful_count += 1
        logger.info("Certificate generated successfully for %s", cert.recipient_name)
    except Exception as exc:
        cert.status = CertificateStatus.FAILED.value
        cert.error_message = _error_text(exc)
        job.failed_count += 1
        logger.error("Certificate generation failed for %s: %s", cert.recipient_name, exc)
    db.commit()


def _abort_job(db: Session, job_id: str, reason: str) -> None:
    """Unexpected processor-level error: close the job out as FAILED, consistently."""
    db.rollback()
    job = db.get(Job, job_id)
    if job is None:
        return

    unfinished = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job_id,
            Certificate.status.in_(
                [CertificateStatus.PENDING.value, CertificateStatus.PROCESSING.value]
            ),
        )
        .all()
    )
    for cert in unfinished:
        cert.status = CertificateStatus.FAILED.value
        cert.error_message = f"Job aborted: {reason}"[:MAX_ERROR_LENGTH]
    db.flush()

    def count(status: CertificateStatus) -> int:
        return (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id, Certificate.status == status.value)
            .count()
        )

    job.successful_count = count(CertificateStatus.SUCCESS)
    job.failed_count = count(CertificateStatus.FAILED)
    job.status = JobStatus.FAILED.value
    job.completed_at = utcnow()
    db.commit()


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
                        .order_by(Certificate.position, Certificate.id)
            .all()
        )

        for cert in certificates:
            _process_certificate(db, job, cert)

        job.status = _final_status(job)
        job.completed_at = utcnow()
        db.commit()
        logger.info(
            "Job %s completed: %s (%d ok, %d failed)",
            job_id, job.status, job.successful_count, job.failed_count,
        )
    except Exception as exc:
        logger.exception("Job %s aborted by unexpected error", job_id)
        try:
            _abort_job(db, job_id, _error_text(exc))
        except Exception:
            logger.exception("Job %s could not be marked as FAILED", job_id)
    finally:
        db.close()