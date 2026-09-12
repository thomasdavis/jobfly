import pytest
from backend.server import validate_jobs


def test_import_rejects_duplicate_identity():
    with pytest.raises(ValueError, match="unique"):
        validate_jobs([{"id": 1, "title": "Engineer", "company": "A"}] * 2)


def test_import_requires_job_identity():
    with pytest.raises(ValueError, match="title and company"):
        validate_jobs([{"description": "Missing identity"}])
