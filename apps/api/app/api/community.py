from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.community import CommunityPost, CommunityStore, get_community_store
from app.config import settings
from app.identity import client_id
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.schemas import (
    CommunityCreateRequest,
    CommunityFeedResponse,
    CommunityModerateResponse,
    CommunityPostResponse,
)

router = APIRouter(prefix="/api", tags=["community"])

DEV_ADMIN_KEY = "dev-admin-key"  # active only when ADMIN_DEV_KEY_ENABLED=1


def _community_limiter() -> RateLimiter:
    return get_rate_limiter("community_ratelimit", 5, 3600)


def _to_response(post: CommunityPost) -> CommunityPostResponse:
    return CommunityPostResponse(
        id=post.id,
        kind=post.kind,
        location=post.location,
        text=post.text,
        status=post.status,
        created_at=post.created_at.isoformat(),
    )


def _require_admin(x_admin_key: str) -> None:
    if settings.admin_key:
        if not secrets.compare_digest(x_admin_key, settings.admin_key):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin key")
    elif settings.app_env == "development" and settings.admin_dev_key_enabled:
        if not secrets.compare_digest(x_admin_key, DEV_ADMIN_KEY):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin key")
    else:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin endpoints disabled")


@router.get("/community", response_model=CommunityFeedResponse)
def community_feed(
    store: Annotated[CommunityStore, Depends(get_community_store)],
    limit: int = Query(default=50, ge=1, le=200),
) -> CommunityFeedResponse:
    return CommunityFeedResponse(posts=[_to_response(p) for p in store.feed(limit)])


@router.post(
    "/community", response_model=CommunityPostResponse, status_code=status.HTTP_201_CREATED
)
def create_community_post(
    payload: CommunityCreateRequest,
    request: Request,
    store: Annotated[CommunityStore, Depends(get_community_store)],
    limiter: Annotated[RateLimiter, Depends(_community_limiter)],
    cid: Annotated[str, Depends(client_id)],
) -> CommunityPostResponse:
    if not limiter.allow(cid):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many community posts")
    post = store.create(cid, payload.kind, payload.location, payload.text)
    return _to_response(post)


@router.post("/admin/community/{post_id}/verify", response_model=CommunityModerateResponse)
def verify_community_post(
    post_id: str,
    store: Annotated[CommunityStore, Depends(get_community_store)],
    x_admin_key: Annotated[str, Header()] = "",
) -> CommunityModerateResponse:
    _require_admin(x_admin_key)
    post = store.set_status(post_id, "VERIFIED")
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown community post")
    return CommunityModerateResponse(id=post.id, status="VERIFIED")


@router.post("/admin/community/{post_id}/reject", response_model=CommunityModerateResponse)
def reject_community_post(
    post_id: str,
    store: Annotated[CommunityStore, Depends(get_community_store)],
    x_admin_key: Annotated[str, Header()] = "",
) -> CommunityModerateResponse:
    _require_admin(x_admin_key)
    post = store.set_status(post_id, "REJECTED")
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown community post")
    return CommunityModerateResponse(id=post.id, status="REJECTED")
