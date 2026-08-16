# API Specification

## GET /health
Returns health status.

## POST /api/routes
Request:
{
  "origin": {"lat": 28.61, "lon": 77.23},
  "destination": {"lat": 28.63, "lon": 77.21},
  "mode": "walking",
  "safety_preference": "safety"
}

Response must include:
route type, distance, duration, risk probability,
estimated safety, confidence, warnings, reasons, model version,
high_risk_fraction (0-1) and risk_exposure_m (0 when segment lengths unknown).
Warnings include an explicit off-network note when origin/destination sit
> 150 m from any mapped road. Per-IP rate limit:
`ROUTE_RATE_LIMIT_PER_MINUTE` (default 30) → 429.

## GET /api/geocode?q=...&limit=6
Place search over monitored areas and mapped facilities. Response:
{"results": [{"name", "kind": "area|facility", "type", "lat", "lon"}]}.
No external geocoding service; empty query returns no results.

## POST /api/reports
Creates an anonymous safety observation.
Required: segment_id, category, timestamp.
Optional: redacted description, evidence image.

## GET /api/segments/{id}/evidence
Returns aggregated evidence, freshness, confidence, source counts,
source-type diversity (distinct_source_types, corroborated) and conflicts.
Never return reporter identity.

## GET /api/admin/reports?limit=50
Admin review queue (`X-Admin-Key` header; 403 without a valid key).
Each report: report_id, segment_id, category, verification_state,
reported_at, confidence. Descriptions, images and client hashes are never
returned. Disabled (503) in production without an `ADMIN_KEY`.

## POST /api/admin/reports/{id}/verify | /reject
Admin-only, `X-Admin-Key` required, audited. Sticky: the state survives
`recompute`. 404 for unknown report ids.

## POST /api/admin/recompute
Admin-only recomputation of affected segments.

## GET /api/models/current
Returns current model metadata and validation status.

## Rules
- Validate coordinates.
- Rate-limit reports and route requests.
- Detect duplicate/spam reports.
- Strip unnecessary image metadata.
- Log model version for route responses.
- Never return `safe=true`.
