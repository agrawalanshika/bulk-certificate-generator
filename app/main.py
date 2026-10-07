from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging
from app.routers import certificates, jobs
from app.utils.validators import validation_exception_handler

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


API_DESCRIPTION = """
Submit **one request with many recipients** and get a PDF certificate for each.

1. `POST /api/jobs` - validate the request, create a job, return a `job_id` immediately.
2. `GET /api/jobs/{job_id}` - track status and progress while certificates generate in the background.
3. `GET /api/jobs/{job_id}/certificates` - see each certificate's result (and error, if any).
4. `GET /api/certificates/{certificate_id}/download` - download a generated PDF.

A failure on one certificate never stops the others.
"""

TAGS_METADATA = [
    {"name": "Jobs", "description": "Create bulk generation jobs and track their progress."},
    {"name": "Certificates", "description": "Retrieve generated certificate PDFs."},
    {"name": "Health", "description": "Service health check."},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(jobs.router)
app.include_router(certificates.router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}