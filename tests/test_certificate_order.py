import datetime as dt

import pytest

from app.models import Certificate

FIXED_TIME = dt.datetime(2026, 10, 7, 12, 0, 0, tzinfo=dt.timezone.utc)


@pytest.fixture()
def identical_timestamps():
    """Give every row the same created_at, like a coarse system clock (e.g. Windows) can."""
    column = Certificate.__table__.c.created_at
    original = column.default.arg
    column.default.arg = lambda ctx: FIXED_TIME
    yield
    column.default.arg = original


def test_certificates_keep_submission_order_even_with_identical_timestamps(client, identical_timestamps):
    names = [f"Person {i:02d}" for i in range(30)]
    body = {
        "title": "T",
        "course": "C",
        "date": "2026-10-07",
        "recipients": [{"name": n, "email": f"p{i}@example.com"} for i, n in enumerate(names)],
    }
    job_id = client.post("/api/jobs", json=body).json()["job_id"]

    listed = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]
    assert [c["recipient"] for c in listed] == names