import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas import JobCreateRequest
from app.utils.validators import validation_exception_handler


def valid_payload(**overrides):
    payload = {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [
            {"name": "Anshika Agrawal", "email": "anshika@example.com"},
            {"name": "Rahul Sharma", "email": "rahul@example.com"},
        ],
    }
    payload.update(overrides)
    return payload


def test_valid_payload_parses():
    req = JobCreateRequest(**valid_payload())
    assert len(req.recipients) == 2
    assert str(req.date) == "2026-10-07"


def test_names_are_trimmed():
    req = JobCreateRequest(
        **valid_payload(recipients=[{"name": "  Priya Singh  ", "email": "priya@example.com"}])
    )
    assert req.recipients[0].name == "Priya Singh"


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_rejected(name):
    with pytest.raises(ValidationError):
        JobCreateRequest(**valid_payload(recipients=[{"name": name, "email": "a@example.com"}]))


@pytest.mark.parametrize("email", ["not-an-email", "a@", "@example.com", ""])
def test_invalid_email_rejected(email):
    with pytest.raises(ValidationError):
        JobCreateRequest(**valid_payload(recipients=[{"name": "A", "email": email}]))


def test_empty_recipient_list_rejected():
    with pytest.raises(ValidationError):
        JobCreateRequest(**valid_payload(recipients=[]))


@pytest.mark.parametrize("field", ["title", "course", "date", "recipients"])
def test_missing_field_rejected(field):
    payload = valid_payload()
    payload.pop(field)
    with pytest.raises(ValidationError):
        JobCreateRequest(**payload)


def test_invalid_date_rejected():
    with pytest.raises(ValidationError):
        JobCreateRequest(**valid_payload(date="not-a-date"))


def test_error_handler_returns_422_with_field_paths():
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.post("/echo")
    def echo(body: JobCreateRequest):
        return {"ok": True}

    client = TestClient(app)
    resp = client.post(
        "/echo",
        json=valid_payload(recipients=[{"name": "A", "email": "bad-email"}]),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"] == "Validation failed"
    assert body["errors"][0]["field"] == "recipients.0.email"