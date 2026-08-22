"""Community posts: anonymous, moderated route updates.

Posts are pseudonymous (keyed by client_id, never exposed in the public feed).
Every post starts PENDING; an admin may mark it VERIFIED or REJECTED. The feed
only ever shows VERIFIED and PENDING posts so unreviewed content is labelled
as unreviewed — nothing here implies an update is fact.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import Engine, text

from app.db import make_engine

logger = logging.getLogger(__name__)

POST_KINDS = ("alert", "route_update", "photo")
POST_STATUSES = ("PENDING", "VERIFIED", "REJECTED")


@dataclass(frozen=True)
class CommunityPost:
    id: str
    client_id: str
    kind: str
    location: str
    text: str
    status: str
    created_at: datetime
    moderated_at: datetime | None = None


@runtime_checkable
class CommunityStore(Protocol):
    def create(
        self, client_id_value: str, kind: str, location: str, body: str
    ) -> CommunityPost: ...

    def feed(self, limit: int) -> Sequence[CommunityPost]: ...

    def set_status(self, post_id: str, status: str) -> CommunityPost | None: ...

    def count_by_status(self) -> dict[str, int]: ...


def _to_post(row: Any) -> CommunityPost:
    return CommunityPost(
        id=str(row[0]),
        client_id=str(row[1]),
        kind=str(row[2]),
        location=str(row[3]),
        text=str(row[4]),
        status=str(row[5]),
        created_at=row[6],
        moderated_at=row[7],
    )


class MemoryCommunityStore:
    """In-memory store (dev/fallback backend)."""

    def __init__(self) -> None:
        self._posts: list[CommunityPost] = []
        self._next_id = 1

    def create(self, client_id_value: str, kind: str, location: str, body: str) -> CommunityPost:
        post = CommunityPost(
            id=f"post-{self._next_id}",
            client_id=client_id_value,
            kind=kind,
            location=location,
            text=body,
            status="PENDING",
            created_at=datetime.now(UTC),
        )
        self._next_id += 1
        self._posts.append(post)
        return post

    def feed(self, limit: int) -> Sequence[CommunityPost]:
        visible = [p for p in self._posts if p.status in ("PENDING", "VERIFIED")]
        return sorted(visible, key=lambda p: p.created_at, reverse=True)[:limit]

    def set_status(self, post_id: str, status: str) -> CommunityPost | None:
        for i, post in enumerate(self._posts):
            if post.id == post_id:
                updated = CommunityPost(
                    id=post.id,
                    client_id=post.client_id,
                    kind=post.kind,
                    location=post.location,
                    text=post.text,
                    status=status,
                    created_at=post.created_at,
                    moderated_at=datetime.now(UTC),
                )
                self._posts[i] = updated
                return updated
        return None

    def count_by_status(self) -> dict[str, int]:
        counts = {"PENDING": 0, "VERIFIED": 0, "REJECTED": 0}
        for post in self._posts:
            counts[post.status] = counts.get(post.status, 0) + 1
        return counts


class PostgresCommunityStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, client_id_value: str, kind: str, location: str, body: str) -> CommunityPost:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO community_posts (client_id, kind, location, text) "
                    "VALUES (:cid, :kind, :location, :text) "
                    "RETURNING id, client_id, kind, location, text, status, created_at, "
                    "moderated_at"
                ),
                {
                    "cid": client_id_value,
                    "kind": kind,
                    "location": location,
                    "text": body,
                },
            ).one()
        return _to_post(row)

    def feed(self, limit: int) -> Sequence[CommunityPost]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, client_id, kind, location, text, status, created_at, "
                    "moderated_at FROM community_posts "
                    "WHERE status IN ('PENDING', 'VERIFIED') "
                    "ORDER BY created_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).all()
        return [_to_post(row) for row in rows]

    def set_status(self, post_id: str, status: str) -> CommunityPost | None:
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "UPDATE community_posts SET status = :status, moderated_at = now() "
                    "WHERE id = :id RETURNING id, client_id, kind, location, text, status, "
                    "created_at, moderated_at"
                ),
                {"status": status, "id": post_id},
            ).one_or_none()
        return _to_post(row) if row is not None else None

    def count_by_status(self) -> dict[str, int]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT status, count(*) FROM community_posts GROUP BY status")
            ).all()
        counts = {"PENDING": 0, "VERIFIED": 0, "REJECTED": 0}
        for status, count in rows:
            counts[str(status)] = int(count)
        return counts


def _make_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=4)
def get_community_store() -> CommunityStore:
    try:
        engine = _make_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM community_posts LIMIT 1"))
        return PostgresCommunityStore(engine)
    except Exception as exc:
        logger.warning("PostGIS unavailable for community posts; using memory store: %s", exc)
        return MemoryCommunityStore()
