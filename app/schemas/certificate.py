from pydantic import BaseModel


class CertificateItem(BaseModel):
    id: str
    recipient: str
    email: str
    status: str
    error: str | None = None


class CertificateListResponse(BaseModel):
    job_id: str
    certificates: list[CertificateItem]