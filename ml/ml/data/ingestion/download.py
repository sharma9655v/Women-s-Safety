"""HTTP download with caching, retry, and checksum validation."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass(frozen=True)
class DownloadResult:
    """Result of downloading a file."""

    url: str
    content: bytes
    checksum: str
    etag: str | None
    last_modified: str | None
    downloaded_at: str
    from_cache: bool


def create_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
    timeout: int = 30,
) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.timeout = timeout
    return session


def download_with_cache(
    url: str,
    cache_dir: Path,
    session: requests.Session | None = None,
    force: bool = False,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> DownloadResult:
    """Download a URL with caching based on ETag/Last-Modified/SHA256."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Safe filename from URL
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_file = cache_dir / f"{url_hash}.cache"
    meta_file = cache_dir / f"{url_hash}.meta"

    session = session or create_session(timeout=timeout)
    default_headers = {"User-Agent": "WomenSafetyDatasetPipeline/1.0"}
    if headers:
        default_headers.update(headers)

    # Load cached metadata
    cached_meta: dict[str, Any] = {}
    if meta_file.exists():
        import json

        cached_meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Check if we can use cache
    if not force and cache_file.exists() and cached_meta:
        # Validate cached file checksum
        cached_content = cache_file.read_bytes()
        cached_checksum = hashlib.sha256(cached_content).hexdigest()
        if cached_checksum == cached_meta.get("checksum"):
            # Check if remote has changed (conditional request)
            conditional_headers = default_headers.copy()
            if cached_meta.get("etag"):
                conditional_headers["If-None-Match"] = cached_meta["etag"]
            if cached_meta.get("last_modified"):
                conditional_headers["If-Modified-Since"] = cached_meta["last_modified"]

            try:
                resp = session.head(url, headers=conditional_headers, timeout=timeout)
                if resp.status_code == 304:
                    return DownloadResult(
                        url=url,
                        content=cached_content,
                        checksum=cached_checksum,
                        etag=cached_meta.get("etag"),
                        last_modified=cached_meta.get("last_modified"),
                        downloaded_at=cached_meta.get("downloaded_at", ""),
                        from_cache=True,
                    )
            except requests.RequestException:
                pass  # Fall through to download

    # Download
    resp = session.get(url, headers=default_headers, timeout=timeout, stream=True)
    resp.raise_for_status()

    content = resp.content
    checksum = hashlib.sha256(content).hexdigest()

    etag = resp.headers.get("ETag")
    last_modified = resp.headers.get("Last-Modified")
    downloaded_at = datetime.now(UTC).isoformat() + "Z"

    # Save to cache
    cache_file.write_bytes(content)
    meta = {
        "url": url,
        "checksum": checksum,
        "etag": etag,
        "last_modified": last_modified,
        "downloaded_at": downloaded_at,
    }
    meta_file.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return DownloadResult(
        url=url,
        content=content,
        checksum=checksum,
        etag=etag,
        last_modified=last_modified,
        downloaded_at=downloaded_at,
        from_cache=False,
    )


def download_multiple(
    urls: list[str],
    cache_dir: Path,
    session: requests.Session | None = None,
    force: bool = False,
    timeout: int = 30,
    delay_between: float = 1.0,
) -> list[DownloadResult]:
    """Download multiple URLs with rate limiting."""
    results = []
    session = session or create_session(timeout=timeout)
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay_between)
        try:
            result = download_with_cache(url, cache_dir, session, force, timeout)
            results.append(result)
        except Exception:
            # Return failed result
            results.append(
                DownloadResult(
                    url=url,
                    content=b"",
                    checksum="",
                    etag=None,
                    last_modified=None,
                    downloaded_at=datetime.now(UTC).isoformat() + "Z",
                    from_cache=False,
                )
            )
    return results
