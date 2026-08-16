"""Trusted contacts API: CRUD, ownership isolation, privacy of phone data."""

from fastapi.testclient import TestClient

from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import MemoryContactStore, MemoryEmergencyStore, MemoryNotificationStore
from app.safety.contacts import get_contacts_store
from app.safety.notifications import get_notification_store
from app.safety.sessions import get_sessions_store

CLIENT_A = "a" * 32
CLIENT_B = "b" * 32


def make_client(*, limit: int = 20) -> TestClient:
    from app.api.contacts import _contacts_limiter

    app.dependency_overrides = {}
    contacts = MemoryContactStore()
    sessions = MemoryEmergencyStore()
    notifications = MemoryNotificationStore()
    limiter = MemoryRateLimiter(limit, 3600)
    app.dependency_overrides[get_contacts_store] = lambda: contacts
    app.dependency_overrides[get_sessions_store] = lambda: sessions
    app.dependency_overrides[get_notification_store] = lambda: notifications
    app.dependency_overrides[_contacts_limiter] = lambda: limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def _contact(name: str = "Mother", phone: str = "+919876543210") -> dict[str, str]:
    return {"name": name, "relationship": "family", "phone": phone, "role": "primary"}


def test_contacts_require_client_id() -> None:
    client = make_client()
    assert client.get("/api/contacts").status_code == 401
    assert client.post("/api/contacts", json=_contact()).status_code == 401


def test_invalid_client_id_rejected() -> None:
    client = make_client()
    resp = client.get("/api/contacts", headers={"X-Client-Id": "not-hex"})
    assert resp.status_code == 400


def test_create_and_list_contact() -> None:
    client = make_client()
    resp = client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Mother"
    assert body["phone"] == "+919876543210"
    assert body["role"] == "primary"
    listed = client.get("/api/contacts", headers=_headers(CLIENT_A)).json()["contacts"]
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_empty_list() -> None:
    client = make_client()
    assert client.get("/api/contacts", headers=_headers(CLIENT_A)).json()["contacts"] == []


def test_update_contact() -> None:
    client = make_client()
    created = client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A)).json()
    resp = client.put(
        f"/api/contacts/{created['id']}",
        json={"name": "Mom", "role": "secondary"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mom"
    assert resp.json()["role"] == "secondary"


def test_delete_contact() -> None:
    client = make_client()
    created = client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A)).json()
    resp = client.delete(f"/api/contacts/{created['id']}", headers=_headers(CLIENT_A))
    assert resp.status_code == 204
    assert client.get("/api/contacts", headers=_headers(CLIENT_A)).json()["contacts"] == []


def test_cross_client_isolation() -> None:
    client = make_client()
    created = client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A)).json()
    assert client.get("/api/contacts", headers=_headers(CLIENT_B)).json()["contacts"] == []
    assert (
        client.put(
            f"/api/contacts/{created['id']}", json={"name": "X"}, headers=_headers(CLIENT_B)
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/contacts/{created['id']}", headers=_headers(CLIENT_B)).status_code
        == 404
    )


def test_invalid_contact_payload_rejected() -> None:
    client = make_client()
    bad = _contact()
    bad["phone"] = "1"
    assert client.post("/api/contacts", json=bad, headers=_headers(CLIENT_A)).status_code == 422
    bad2 = _contact()
    bad2["role"] = "godfather"
    assert client.post("/api/contacts", json=bad2, headers=_headers(CLIENT_A)).status_code == 422


def test_contact_updates_rate_limited() -> None:
    client = make_client(limit=2)
    client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A))
    client.post("/api/contacts", json=_contact("Sister"), headers=_headers(CLIENT_A))
    resp = client.post("/api/contacts", json=_contact("Friend"), headers=_headers(CLIENT_A))
    assert resp.status_code == 429


def test_phone_encryption_mechanism_roundtrips() -> None:
    from app.reports.redact import decrypt_blob, encrypt_blob

    client = make_client()
    client.post("/api/contacts", json=_contact(), headers=_headers(CLIENT_A))
    raw = client.get("/api/contacts", headers=_headers(CLIENT_A)).json()["contacts"][0]
    assert raw["phone"] == "+919876543210"  # decrypted for the owner
    # at rest (Postgres store) the phone is Fernet-encrypted, never plaintext
    ciphertext = encrypt_blob(b"+919876543210")
    assert b"+919876543210" not in ciphertext
    assert decrypt_blob(ciphertext) == b"+919876543210"
