"""Trusted contacts. Phone numbers are encrypted at rest (Fernet) — the only
personal data in this feature. Never exposed publicly; API responses return
the number only to the owning client."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, Row, text

from app.db import make_engine
from app.reports.redact import decrypt_blob, encrypt_blob

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Contact:
    id: int
    client_id: str
    name: str
    relationship: str
    phone: str
    role: str
    enabled: bool
    created_at: datetime | None = None


def _to_contact(row: Row[Any]) -> Contact:
    return Contact(
        id=int(row[0]),
        client_id=str(row[1]),
        name=str(row[2]),
        relationship=str(row[3]),
        phone=decrypt_blob(bytes(row[4])).decode("utf-8"),
        role=str(row[5]),
        enabled=bool(row[6]),
        created_at=row[7],
    )


class ContactStore:
    def list(self, client_id_value: str) -> Sequence[Contact]:
        raise NotImplementedError

    def create(
        self,
        client_id_value: str,
        name: str,
        relationship: str,
        phone: str,
        role: str,
    ) -> Contact:
        raise NotImplementedError

    def update(
        self,
        client_id_value: str,
        contact_id: int,
        *,
        name: str | None = None,
        relationship: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        enabled: bool | None = None,
    ) -> Contact | None:
        raise NotImplementedError

    def delete(self, client_id_value: str, contact_id: int) -> bool:
        raise NotImplementedError


class MemoryContactStore(ContactStore):
    def __init__(self) -> None:
        self._contacts: dict[int, Contact] = {}
        self._next_id = 1

    def list(self, client_id_value: str) -> Sequence[Contact]:
        return [c for c in self._contacts.values() if c.client_id == client_id_value]

    def create(
        self,
        client_id_value: str,
        name: str,
        relationship: str,
        phone: str,
        role: str,
    ) -> Contact:
        contact = Contact(
            id=self._next_id,
            client_id=client_id_value,
            name=name,
            relationship=relationship,
            phone=phone,
            role=role,
            enabled=True,
            created_at=datetime.now(UTC),
        )
        self._next_id += 1
        self._contacts[contact.id] = contact
        return contact

    def update(
        self,
        client_id_value: str,
        contact_id: int,
        *,
        name: str | None = None,
        relationship: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        enabled: bool | None = None,
    ) -> Contact | None:
        existing = self._contacts.get(contact_id)
        if existing is None or existing.client_id != client_id_value:
            return None
        updated = Contact(
            id=existing.id,
            client_id=existing.client_id,
            name=name or existing.name,
            relationship=relationship or existing.relationship,
            phone=phone or existing.phone,
            role=role or existing.role,
            enabled=existing.enabled if enabled is None else enabled,
            created_at=existing.created_at,
        )
        self._contacts[contact_id] = updated
        return updated

    def delete(self, client_id_value: str, contact_id: int) -> bool:
        existing = self._contacts.get(contact_id)
        if existing is None or existing.client_id != client_id_value:
            return False
        del self._contacts[contact_id]
        return True


class PostgresContactStore(ContactStore):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list(self, client_id_value: str) -> Sequence[Contact]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, client_id, name, relationship, phone_encrypted, role, "
                    "enabled, created_at FROM trusted_contacts WHERE client_id = :cid "
                    "ORDER BY role DESC, created_at"
                ),
                {"cid": client_id_value},
            ).all()
        return [_to_contact(row) for row in rows]

    def create(
        self,
        client_id_value: str,
        name: str,
        relationship: str,
        phone: str,
        role: str,
    ) -> Contact:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO trusted_contacts (client_id, name, relationship, "
                    "phone_encrypted, role) VALUES (:cid, :name, :rel, :phone, :role) "
                    "RETURNING id, client_id, name, relationship, phone_encrypted, role, "
                    "enabled, created_at"
                ),
                {
                    "cid": client_id_value,
                    "name": name,
                    "rel": relationship,
                    "phone": encrypt_blob(phone.encode("utf-8")),
                    "role": role,
                },
            ).one()
        return _to_contact(row)

    def update(
        self,
        client_id_value: str,
        contact_id: int,
        *,
        name: str | None = None,
        relationship: str | None = None,
        phone: str | None = None,
        role: str | None = None,
        enabled: bool | None = None,
    ) -> Contact | None:
        sets = []
        params: dict[str, object] = {
            "cid": client_id_value,
            "cid2": client_id_value,
            "id": contact_id,
        }
        if name is not None:
            sets.append("name = :name")
            params["name"] = name
        if relationship is not None:
            sets.append("relationship = :rel")
            params["rel"] = relationship
        if phone is not None:
            sets.append("phone_encrypted = :phone")
            params["phone"] = encrypt_blob(phone.encode("utf-8"))
        if role is not None:
            sets.append("role = :role")
            params["role"] = role
        if enabled is not None:
            sets.append("enabled = :enabled")
            params["enabled"] = enabled
        if not sets:
            return self._get(client_id_value, contact_id)
        sets.append("updated_at = now()")
        stmt = (
            "UPDATE trusted_contacts SET "
            + ", ".join(sets)
            + " WHERE id = :id AND client_id = :cid RETURNING id, client_id, name, "
            "relationship, phone_encrypted, role, enabled, created_at"
        )
        with self._engine.begin() as conn:
            row = conn.execute(text(stmt), params).one_or_none()
        return _to_contact(row) if row is not None else None

    def _get(self, client_id_value: str, contact_id: int) -> Contact | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, client_id, name, relationship, phone_encrypted, role, "
                    "enabled, created_at FROM trusted_contacts WHERE id = :id AND client_id = :cid"
                ),
                {"id": contact_id, "cid": client_id_value},
            ).one_or_none()
        return _to_contact(row) if row is not None else None

    def delete(self, client_id_value: str, contact_id: int) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM trusted_contacts WHERE id = :id AND client_id = :cid"),
                {"id": contact_id, "cid": client_id_value},
            )
        return result.rowcount > 0


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_contacts_store() -> ContactStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM trusted_contacts LIMIT 1"))
        return PostgresContactStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for contacts; using memory store: %s", exc)
        return MemoryContactStore()
