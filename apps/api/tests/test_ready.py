from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ready_returns_200_when_components_ok(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", "")

    import httpx

    class _FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get(self, url: str) -> object:
            class _Response:
                status_code = 200

            return _Response()

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    from app.cv.registry import get_cv_service

    get_cv_service.cache_clear()
    resp = client.get("/ready")
    get_cv_service.cache_clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"]["osrm"] == "ok"
    assert body["components"]["cv"] == "ok"


def test_ready_returns_503_when_osrm_down(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", "")

    import httpx

    class _FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get(self, url: str) -> object:
            class _Response:
                status_code = 502

            return _Response()

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    resp = client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["components"]["osrm"].startswith("error")


def test_ready_omits_database_when_not_configured(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", "")
    import httpx

    class _FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get(self, url: str) -> object:
            class _Response:
                status_code = 200

            return _Response()

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    resp = client.get("/ready")
    body = resp.json()
    assert "database" not in body["components"]
