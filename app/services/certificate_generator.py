import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.config import settings
from app.models import Certificate, Job

logger = logging.getLogger(__name__)

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
NAVY = colors.HexColor("#1F3A5F")
GOLD = colors.HexColor("#B8860B")
GREY = colors.HexColor("#555555")


def build_certificate_path(job_id: str, certificate_id: str, output_dir: str | None = None) -> Path:
    base = Path(output_dir or settings.generated_dir)
    return base / f"job_{job_id}" / f"certificate_{certificate_id}.pdf"


def _fit_font_size(text: str, font: str, max_size: int, max_width: float) -> int:
    size = max_size
    while size > 12 and stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _draw_template(c: canvas.Canvas, *, title: str, name: str, course: str,
                   date_text: str, certificate_id: str) -> None:
    cx = PAGE_WIDTH / 2
    max_text_width = PAGE_WIDTH - 140

    # Double border
    c.setStrokeColor(NAVY)
    c.setLineWidth(4)
    c.rect(25, 25, PAGE_WIDTH - 50, PAGE_HEIGHT - 50)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.rect(36, 36, PAGE_WIDTH - 72, PAGE_HEIGHT - 72)

    # Title
    c.setFillColor(NAVY)
    size = _fit_font_size(title.upper(), "Helvetica-Bold", 34, max_text_width)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(cx, PAGE_HEIGHT - 120, title.upper())

    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(cx - 120, PAGE_HEIGHT - 135, cx + 120, PAGE_HEIGHT - 135)

    # Body
    c.setFillColor(GREY)
    c.setFont("Helvetica", 16)
    c.drawCentredString(cx, PAGE_HEIGHT - 190, "This is to certify that")

    c.setFillColor(NAVY)
    size = _fit_font_size(name, "Helvetica-Bold", 40, max_text_width)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(cx, PAGE_HEIGHT - 245, name)
    name_width = stringWidth(name, "Helvetica-Bold", size)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(cx - name_width / 2 - 10, PAGE_HEIGHT - 255, cx + name_width / 2 + 10, PAGE_HEIGHT - 255)

    c.setFillColor(GREY)
    c.setFont("Helvetica", 16)
    c.drawCentredString(cx, PAGE_HEIGHT - 295, "has successfully completed")

    c.setFillColor(NAVY)
    size = _fit_font_size(course, "Helvetica-Bold", 26, max_text_width)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(cx, PAGE_HEIGHT - 335, course)

    c.setFillColor(GREY)
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, PAGE_HEIGHT - 380, f"Date: {date_text}")

    # Footer
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, 52, f"Certificate ID: {certificate_id}")


def generate_certificate(certificate: Certificate, job: Job, output_dir: str | None = None) -> str:
    """Render one certificate PDF to disk and return its file path.

    Raises on failure; the caller decides how to record it.
    """
    path = build_certificate_path(job.id, certificate.id, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    # pageCompression=0 keeps text streams uncompressed (tiny files, and testable)
    c = canvas.Canvas(str(path), pagesize=landscape(A4), pageCompression=0)
    c.setTitle(f"{job.title} - {certificate.recipient_name}")
    _draw_template(
        c,
        title=job.title,
        name=certificate.recipient_name,
        course=job.course,
        date_text=job.issue_date.strftime("%d/%m/%Y"),
        certificate_id=certificate.id,
    )
    c.showPage()
    c.save()

    logger.info("Generated certificate %s for %s", certificate.id, certificate.recipient_name)
    return str(path)