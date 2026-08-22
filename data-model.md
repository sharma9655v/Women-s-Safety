# Data Model

## road_segments
id, osm_way_id, geometry, road_type, lit_osm, created_at, updated_at

## safety_observations
id, segment_id, source_type, observation_type, value_json,
observed_at, ingested_at, source_reliability, confidence,
verification_state, expires_at, evidence_hash

## safety_reports
id, segment_id, category, description_redacted,
reported_at, verification_state, confidence, created_at

Categories:
streetlight_not_working
poor_lighting
harassment
suspicious_activity
blocked_sidewalk
unsafe_transport
road_hazard
other

## facilities
id, osm_id, type, name, geometry, operational_status, updated_at

Types:
police, hospital, pharmacy, fire_station, transit_stop, public_place

## route_requests
id, origin, destination, mode, safety_preference, requested_at

## route_results
id, request_id, route_type, distance_m, duration_s,
risk_score, confidence, uncertainty, explanation_json, model_version

## model_versions
id, name, version, trained_at, dataset_version, metrics_json, status

Never overwrite model versions.
