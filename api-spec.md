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
estimated safety, confidence, warnings, reasons, model version.

## POST /api/reports
Creates an anonymous safety observation.
Required: segment_id, category, timestamp.
Optional: redacted description, evidence image.

## GET /api/segments/{id}/evidence
Returns aggregated evidence, freshness, confidence, source counts and conflicts.
Never return reporter identity.

## POST /api/admin/recompute
Admin-only recomputation of affected segments.

## GET /api/models/current
Returns current model metadata and validation status.

## Rules
- Validate coordinates.
- Rate-limit reports.
- Detect duplicate/spam reports.
- Strip unnecessary image metadata.
- Log model version for route responses.
- Never return `safe=true`.
