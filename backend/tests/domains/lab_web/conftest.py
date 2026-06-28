"""Fixtures for lab_web tests."""
from __future__ import annotations

import pytest

from app.domains.lab_web.models.lab_web import LWLabRegistry


@pytest.fixture
async def sample_lab(test_session):
    """A single active lab in the registry."""
    lab = LWLabRegistry(
        lab_code="test_lab",
        lab_name="Test Lab",
        lab_name_en="Test Lab",
        institution="Test University",
        country="US",
        people_url="https://example.test/people/",
        collector_class="labs.test.TestCollector",
        fetch_mode="static",
        is_active=True,
    )
    test_session.add(lab)
    await test_session.commit()
    await test_session.refresh(lab)
    return lab
