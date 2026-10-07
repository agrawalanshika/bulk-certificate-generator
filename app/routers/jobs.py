import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, Job
from app.schemas import (
    CertificateItem,
    CertificateListResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
)
from app.services.job_processor import process_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_job_or_404(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


def calculate_progress(job: Job) -> int:
    if job.total_recipients == 0:
        return 0
    processed = job.successful_count + job.failed_count
    return min(100, int(processed * 100 / job.total_recipients))


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bulk certificate generation job",
    description=(
        "Accepts one request containing many recipients. The whole request is validated "
        "first (any invalid recipient rejects it with 422). A job is then created and "
        "certificates are generated **in the background**; the response returns "
        "immediately with a `job_id`. Poll `GET /api/jobs/{job_id}` for progress."
    ),
    responses={422: {"description": "Validation failed (details listed per field)"}},
)
def create_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = Job(
        title=payload.title,
        course=payload.course,
        issue_date=payload.date,
        total_recipients=len(payload.recipients),
    )
    job.certificates = [
        Certificate(position=i, recipient_name=r.name, recipient_email=r.email)
        for i, r in enumerate(payload.recipients)
    ]
    db.add(job)
    db.commit()
    logger.info("Job %s created with %d recipients", job.id, job.total_recipients)

    # Generation runs after the response is sent; client polls for status.
    background_tasks.add_task(process_job, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and progress",
    description=(
        "Returns overall status (`PENDING`, `PROCESSING`, `COMPLETED`, "
        "`COMPLETED_WITH_ERRORS`, `FAILED`), success/failure counts and "
        "`progress` (0-100, share of certificates already processed)."
    ),
    responses={404: {"description": "Job not found"}},
)
def get_job_status(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = get_job_or_404(db, job_id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_recipients,
        successful=job.successful_count,
        failed=job.failed_count,
        progress=calculate_progress(job),
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=CertificateListResponse,
    summary="List all certificates of a job",
    description="Per-certificate status. Failed certificates include an `error` message.",
    responses={404: {"description": "Job not found"}},
)
def list_job_certificates(job_id: str, db: Session = Depends(get_db)) -> CertificateListResponse:
    job = get_job_or_404(db, job_id)
    certificates = (
        db.query(Certificate)
        .filter(Certificate.job_id == job.id)
        .order_by(Certificate.created_at, Certificate.id)
        .all()
    )
    return CertificateListResponse(
        job_id=job.id,
        certificates=[
            CertificateItem(
                id=c.id,
                recipient=c.recipient_name,
                email=c.recipient_email,
                status=c.status,
                error=c.error_message,
            )
            for c in certificates
        ],
    )