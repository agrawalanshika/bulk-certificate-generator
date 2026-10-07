from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

MAX_RECIPIENTS = 1000


class RecipientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255, examples=["Anshika Agrawal"])
    email: EmailStr = Field(examples=["anshika@example.com"])


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "Certificate of Completion",
                "course": "AI/ML Workshop",
                "date": "2026-10-07",
                "recipients": [
                    {"name": "Anshika Agrawal", "email": "anshika@example.com"},
                    {"name": "Rahul Sharma", "email": "rahul@example.com"},
                ],
            }
        },
    )

    title: str = Field(min_length=1, max_length=200)
    course: str = Field(min_length=1, max_length=200)
    date: date
    recipients: list[RecipientIn] = Field(min_length=1, max_length=MAX_RECIPIENTS)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total: int
    successful: int
    failed: int
    progress: int