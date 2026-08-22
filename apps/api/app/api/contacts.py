"""Trusted contacts (Phase 9). Pseudonymous client identity via X-Client-Id.
Contacts are private to their owner; no endpoint exposes another client's
contacts. Phone numbers are encrypted at rest."""

from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety.contacts import Contact, ContactStore, get_contacts_store
from app.schemas import (
    TrustedContact,
    TrustedContactInput,
    TrustedContactListResponse,
    TrustedContactUpdate,
)

router = APIRouter(prefix="/api", tags=["contacts"])


def _contacts_limiter() -> RateLimiter:
    return get_rate_limiter("contact_ratelimit", 20, 3600)


def _to_contact(contact: Contact) -> TrustedContact:
    return TrustedContact(
        id=contact.id,
        name=contact.name,
        relationship=contact.relationship,
        phone=contact.phone,
        role=cast(Literal["primary", "secondary"], contact.role),
        enabled=contact.enabled,
    )


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many contact updates")


@router.get("/contacts", response_model=TrustedContactListResponse)
def list_contacts(
    request: Request,
    store: Annotated[ContactStore, Depends(get_contacts_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> TrustedContactListResponse:
    contacts = [_to_contact(c) for c in store.list(cid)]
    return TrustedContactListResponse(contacts=contacts)


@router.post("/contacts", status_code=status.HTTP_201_CREATED, response_model=TrustedContact)
def create_contact(
    payload: TrustedContactInput,
    request: Request,
    store: Annotated[ContactStore, Depends(get_contacts_store)],
    limiter: Annotated[RateLimiter, Depends(_contacts_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> TrustedContact:
    _require_limit(limiter, cid)
    contact = store.create(cid, payload.name, payload.relationship, payload.phone, payload.role)
    return _to_contact(contact)


@router.put("/contacts/{contact_id}", response_model=TrustedContact)
def update_contact(
    contact_id: int,
    payload: TrustedContactUpdate,
    request: Request,
    store: Annotated[ContactStore, Depends(get_contacts_store)],
    limiter: Annotated[RateLimiter, Depends(_contacts_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> TrustedContact:
    _require_limit(limiter, cid)
    contact = store.update(
        cid,
        contact_id,
        name=payload.name,
        relationship=payload.relationship,
        phone=payload.phone,
        role=payload.role,
        enabled=payload.enabled,
    )
    if contact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown contact")
    return _to_contact(contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int,
    request: Request,
    store: Annotated[ContactStore, Depends(get_contacts_store)],
    limiter: Annotated[RateLimiter, Depends(_contacts_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> None:
    _require_limit(limiter, cid)
    if not store.delete(cid, contact_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown contact")
