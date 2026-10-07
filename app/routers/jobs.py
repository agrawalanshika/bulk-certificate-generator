import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, Job
from app.schemas import JobCreateRequest, JobCreateResponse
from app.services.job_processor import process_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bulk certificate generation job",
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
        Certificate(recipient_name=r.name, recipient_email=r.email)
        for r in payload.recipients
    ]
    db.add(job)
    db.commit()
    logger.info("Job %s created with %d recipients", job.id, job.total_recipients)

    # Generation runs after the response is sent; client polls for status.
    background_tasks.add_task(process_job, job.id)
    return JobCreateResponse(job_id=job.id, status=job.status)