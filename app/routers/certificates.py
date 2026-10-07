import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}/download",
    response_class=FileResponse,
    summary="Download a generated certificate PDF",
    responses={
        200: {"content": {"application/pdf": {}}},
        404: {"description": "Certificate or file not found"},
        409: {"description": "Certificate not generated (pending, processing or failed)"},
    },
)
def download_certificate(certificate_id: str, db: Session = Depends(get_db)) -> FileResponse:
    cert = db.get(Certificate, certificate_id)
    if cert is None:
        raise HTTPException(status_code=404, detail=f"Certificate '{certificate_id}' not found")

    if cert.status != CertificateStatus.SUCCESS.value:
        raise HTTPException(
            status_code=409,
            detail=f"Certificate is not available (status: {cert.status})",
        )

    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(status_code=404, detail="Certificate file not found on server")

    return FileResponse(
        cert.file_path,
        media_type="application/pdf",
        filename=f"certificate_{cert.id}.pdf",
    )