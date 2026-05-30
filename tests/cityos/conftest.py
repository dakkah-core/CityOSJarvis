"""Shared test fixtures for CityOSJarvis backend tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_log_dir():
    """Provide a temporary directory for audit logs."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def mock_tenant_context():
    """Return a mock tenant context for testing."""
    from openjarvis.cityos.tenant import TenantContext

    return TenantContext(
        tenant_id="tenant-42",
        node_path="global/sa/riyadh/dakkah/zone-7/poi-42",
        realm_roles=["city-admin", "ai-user"],
        user_sub="user-123",
    )


@pytest.fixture
def mock_request_with_auth():
    """Return a mock Starlette request with cityos_user state."""
    from unittest.mock import MagicMock

    request = MagicMock()
    request.state.cityos_user = {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "realm_roles": ["city-admin", "ai-user"],
        "tenant_id": "tenant-42",
        "node_path": "global/sa/riyadh/dakkah/zone-7/poi-42",
    }
    return request


@pytest.fixture
def mock_request_no_auth():
    """Return a mock Starlette request without auth state."""
    from unittest.mock import MagicMock

    request = MagicMock()
    request.state = MagicMock()
    # No cityos_user attribute
    return request
