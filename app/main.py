from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import init_db
from app.utils.validators import validation_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for bulk certificate generation with job tracking.",
    lifespan=lifespan,
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}