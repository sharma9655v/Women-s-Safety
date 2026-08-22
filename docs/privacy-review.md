# Privacy review (Phase 8d)

Checklist with the evidence for each item. "Test" = verified in the test
suite; "Live" = verified against the running Docker stack.

## 1. Reporter identity is never collected or stored
- [x] `POST /api/reports` accepts only `segment_id`, `category`, `description`,
      `evidence_image`. No name/phone/email/device fields exist in
      `ReportRequest` (`app/schemas.py`).
- [x] The only server-side identifier is `client_key` = first 16 hex chars of
      sha256(reporter IP) (`app/reports/limiter.py`); it is used for rate
      limiting/duplicates only and is not reversible.
- [x] `client_hash` column stores that hash; the raw IP never touches the DB.
- [x] Evidence API responses are aggregates only (`SegmentEvidenceResponse`):
      counts, scores, freshness, conflicts. No descriptions, no identities.
      Test: `test_report_created_and_content_free` asserts the response body
      contains none of `description/email/phone/identity/ip/image/reporter`.

## 2. Free-text descriptions are redacted server-side
- [x] Emails, phone numbers, URLs and IPv4/IPv6 addresses are replaced with
      `[redacted]` before persistence (`app/reports/redact.py`).
- [x] Live evidence: report with "call me at 98765 43210 or support@x.com"
      stored as "call me at [redacted] or [redacted]".
- [x] Redaction is unit-tested (`test_redact_*`).

## 3. Images are stripped and encrypted at rest
- [x] `strip_image_metadata` re-encodes through Pillow, dropping EXIF and any
      embedded profile; non-image input raises 422 (`app/reports/redact.py`).
- [x] `evidence_image_encrypted` stores Fernet-encrypted bytes
      (`encrypt_blob`); key from `REPORT_ENCRYPTION_KEY` env (dev fallback is a
      documented, code-local constant).
- [x] Encrypted bytes are never returned by any endpoint.

## 4. Rate limiting and duplicate detection protect the store
- [x] 5 reports/hour/client (configurable) enforced by Redis sliding/fixed
      window with in-memory fallback (`app/reports/limiter.py`).
- [x] Duplicate detection: sha256(segment|category|redacted description|client)
      within 24 h returns 409 (`app/reports/spam.py`).
- [x] Tests: 5 accepted then 429; same key again → 409.

## 5. Evidence history is append-only
- [x] DB triggers mirror every observation state change into
      `safety_observation_history` and segment changes into
      `road_segment_history`; rows are never updated in place
      (`schema.sql`).
- [x] Live: 506 history rows after seeding; `recompute` writes only state
      transitions.

## 6. Admin actions are audited
- [x] `admin_audit_log` records action, sha256 of the admin key, and a
      details JSON (`POST /api/admin/recompute`).
- [x] The raw admin key is never stored (test asserts this).
- [x] Live: recompute logged with hashed key, recomputed=0, segments=82.

## 7. No safety guarantee is ever emitted
- [x] API responses contain risk estimates and `estimated_safety` as an
      integer score — never a boolean "safe" field (api-spec.md rule).
- [x] Route responses embed `model_version` for auditability.

## 8. Data minimization
- [x] Observations store typed `value_json`, not free text; report
      descriptions are the only free text and are redacted.
- [x] `GET /api/evidence/segments/{id}` exposes counts/scores only.

## Known limitations (honest)
- The dev fallback admin key `dev-admin-key` is accepted only when
  `app_env == "development"`; production returns 503 without `ADMIN_KEY`.
- Encryption key rotation is manual (set `REPORT_ENCRYPTION_KEY`); a future
  step could add key versioning. No automatic rotation exists today.
- Rate limits are per-IP-hash; a distributed attacker across many IPs is
  outside the current threat model.
- Admin audit has no UI — review via SQL.
