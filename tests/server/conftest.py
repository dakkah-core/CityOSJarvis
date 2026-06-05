"""Server test cleanup helpers."""

from __future__ import annotations

import gc

import pytest


@pytest.fixture(autouse=True)
def _disable_external_analytics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server route tests should not start external analytics workers."""
    monkeypatch.setattr(
        "openjarvis.analytics.is_analytics_enabled",
        lambda _cfg: False,
    )
    monkeypatch.setattr(
        "openjarvis.analytics.client.is_analytics_enabled",
        lambda _cfg: False,
    )


@pytest.fixture(autouse=True)
def _close_test_clients() -> None:
    """Close leaked TestClient instances so lifespan worker threads exit."""
    yield
    try:
        from starlette.testclient import TestClient
    except ImportError:
        return

    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, TestClient):
            try:
                obj.close()
            except Exception:
                pass
