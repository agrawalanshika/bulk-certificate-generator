from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for bulk certificate generation with job tracking.",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}