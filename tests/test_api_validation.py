import pytest

from app.models import Job


def valid(**overrides):
    payload = {
        "title": "Certificate of Completion",
        "course": "AI/ML Workshop",
        "date": "2026-10-07",
        "recipients": [{"name": "Anshika Agrawal", "email": "anshika@example.com"}],
    }
    payload.update(overrides)
    return payload


def errors_by_field(resp):
    return {e["field"]: e["message"] for e in resp.json()["errors"]}


def test_valid_request_is_accepted(client):
    assert client.post("/api/jobs", json=valid()).status_code == 201


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_returns_422(client, db_session, name):
    resp = client.post("/api/jobs", json=valid(recipients=[{"name": name, "email": "a@example.com"}]))
    assert resp.status_code == 422
    assert "recipients.0.name" in errors_by_field(resp)
    assert db_session.query(Job).count() == 0


@pytest.mark.parametrize("email", ["not-an-email", "a@", "@example.com", "a b@example.com", ""])
def test_invalid_email_returns_422(client, db_session, email):
    resp = client.post("/api/jobs", json=valid(recipients=[{"name": "A", "email": email}]))
    assert resp.status_code == 422
    assert "recipients.0.email" in errors_by_field(resp)
    assert db_session.query(Job).count() == 0


@pytest.mark.parametrize("missing", ["title", "course", "date", "recipients"])
def test_missing_top_level_field_returns_422(client, missing):
    payload = valid()
    del payload[missing]
    resp = client.post("/api/jobs", json=payload)
    assert resp.status_code == 422
    assert missing in errors_by_field(resp)


@pytest.mark.parametrize("missing", ["name", "email"])
def test_missing_recipient_field_returns_422(client, missing):
    recipient = {"name": "A", "email": "a@example.com"}
    del recipient[missing]
    resp = client.post("/api/jobs", json=valid(recipients=[recipient]))
    assert resp.status_code == 422
    assert f"recipients.0.{missing}" in errors_by_field(resp)


def test_empty_recipient_list_returns_422(client):
    resp = client.post("/api/jobs", json=valid(recipients=[]))
    assert resp.status_code == 422
    assert "recipients" in errors_by_field(resp)


def test_too_many_recipients_returns_422(client):
    many = [{"name": f"P{i}", "email": f"p{i}@example.com"} for i in range(1001)]
    assert client.post("/api/jobs", json=valid(recipients=many)).status_code == 422


def test_invalid_date_returns_422(client):
    resp = client.post("/api/jobs", json=valid(date="07-13-2026"))
    assert resp.status_code == 422
    assert "date" in errors_by_field(resp)


def test_blank_title_returns_422(client):
    assert client.post("/api/jobs", json=valid(title="   ")).status_code == 422


def test_malformed_json_returns_422(client):
    resp = client.post("/api/jobs", content="{bad json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422
    assert errors_by_field(resp) == {"body": "Request body is not valid JSON"}


def test_missing_body_returns_422(client):
    assert client.post("/api/jobs").status_code == 422


def test_one_invalid_recipient_rejects_whole_request(client, db_session):
    recipients = [
        {"name": "Good", "email": "good@example.com"},
        {"name": "Bad", "email": "bad-email"},
        {"name": "Also Good", "email": "good2@example.com"},
    ]
    resp = client.post("/api/jobs", json=valid(recipients=recipients))
    assert resp.status_code == 422
    assert list(errors_by_field(resp)) == ["recipients.1.email"]
    assert db_session.query(Job).count() == 0


def test_error_response_shape(client):
    body = client.post("/api/jobs", json=valid(recipients=[])).json()
    assert body["detail"] == "Validation failed"
    assert all({"field", "message"} <= set(e) for e in body["errors"])