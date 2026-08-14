-- Map for Women — Phase 2 schema (PostGIS).
-- Canonical DDL for road_segments and facilities, with lineage columns and
-- append-only history. Applied by infra/loaders when PostGIS is available.

CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------------
-- road_segments: OSM-derived road geometry, one row per way (or way part).
-- Every row records where it came from (data_source) and which dataset
-- version (manifest in data/versions/) it belongs to.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS road_segments (
    id              BIGSERIAL PRIMARY KEY,
    osm_way_id      BIGINT NOT NULL,
    geometry        GEOMETRY(LINESTRING, 4326) NOT NULL,
    road_type       TEXT,
    lit             TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_source     TEXT NOT NULL DEFAULT 'osm',
    dataset_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_road_segments_geom ON road_segments USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_road_segments_osm ON road_segments (osm_way_id);

-- Append-only history: any insert/update is mirrored here; rows are never
-- modified in place, only appended. Preserves evidence of previous geometry.
CREATE TABLE IF NOT EXISTS road_segment_history (
    id              BIGSERIAL PRIMARY KEY,
    segment_id      BIGINT NOT NULL,
    osm_way_id      BIGINT NOT NULL,
    geometry        GEOMETRY(LINESTRING, 4326) NOT NULL,
    road_type       TEXT,
    lit             TEXT,
    changed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    data_source     TEXT NOT NULL,
    dataset_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_road_segment_history_seg ON road_segment_history (segment_id);
CREATE INDEX IF NOT EXISTS idx_road_segment_history_geom ON road_segment_history USING GIST (geometry);

CREATE OR REPLACE FUNCTION fn_road_segment_history() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO road_segment_history (segment_id, osm_way_id, geometry, road_type, lit, data_source, dataset_version)
    VALUES (NEW.id, NEW.osm_way_id, NEW.geometry, NEW.road_type, NEW.lit, NEW.data_source, NEW.dataset_version);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_road_segment_history ON road_segments;
CREATE TRIGGER trg_road_segment_history
    AFTER INSERT OR UPDATE ON road_segments
    FOR EACH ROW EXECUTE FUNCTION fn_road_segment_history();

-- ---------------------------------------------------------------------------
-- facilities: POIs relevant to route risk (emergency services, transit).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facilities (
    id                 BIGSERIAL PRIMARY KEY,
    osm_id             BIGINT NOT NULL,
    type               TEXT NOT NULL CHECK (type IN (
        'police', 'hospital', 'pharmacy', 'fire_station', 'transit_stop', 'public_place'
    )),
    name               TEXT,
    geometry           GEOMETRY(POINT, 4326) NOT NULL,
    operational_status TEXT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    dataset_version    TEXT NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_facilities_geom ON facilities USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities (type);

-- ---------------------------------------------------------------------------
-- Phase 3: evidence. Observations are append-only at the row level (an
-- observation row is never deleted); every state change is mirrored into
-- safety_observation_history. Reporter identity is never stored.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_sources (
    id         BIGSERIAL PRIMARY KEY,
    source_type TEXT NOT NULL UNIQUE,
    reliability REAL NOT NULL CHECK (reliability >= 0 AND reliability <= 1),
    description TEXT
);

INSERT INTO data_sources (source_type, reliability, description) VALUES
    ('city_data', 0.90, 'Official city infrastructure data (streetlight maintenance etc.)'),
    ('osm_lighting', 0.70, 'OpenStreetMap lighting tags; moderate reliability, can be stale'),
    ('street_audit', 0.95, 'Verified field audits (future)'),
    ('user_report', 0.60, 'Single anonymous user report'),
    ('weather', 0.90, 'Weather-service derived signals')
ON CONFLICT (source_type) DO NOTHING;

CREATE TABLE IF NOT EXISTS safety_observations (
    id                BIGSERIAL PRIMARY KEY,
    segment_id        BIGINT NOT NULL REFERENCES road_segments(id) ON DELETE CASCADE,
    source_type       TEXT NOT NULL,
    observation_type  TEXT NOT NULL,
    value_json        JSONB NOT NULL DEFAULT '{}',
    observed_at       TIMESTAMPTZ NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_reliability REAL NOT NULL DEFAULT 0.6 CHECK (source_reliability >= 0 AND source_reliability <= 1),
    confidence        REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    verification_state TEXT NOT NULL DEFAULT 'REPORTED' CHECK (
        verification_state IN ('VERIFIED', 'REPORTED', 'CORROBORATED', 'CONFLICTING', 'EXPIRED', 'REJECTED')
    ),
    expires_at        TIMESTAMPTZ,
    evidence_hash     TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_safety_observations_segment ON safety_observations (segment_id, observation_type);

-- Append-only history of every observation state change (evidence_hash makes
-- each history row verifiable; rows are never modified in place).
CREATE TABLE IF NOT EXISTS safety_observation_history (
    id                BIGSERIAL PRIMARY KEY,
    observation_id    BIGINT NOT NULL,
    segment_id        BIGINT NOT NULL,
    verification_state TEXT NOT NULL,
    confidence        REAL NOT NULL,
    changed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    evidence_hash     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_safety_obs_history_obs ON safety_observation_history (observation_id);
CREATE INDEX IF NOT EXISTS idx_safety_obs_history_seg ON safety_observation_history (segment_id);

CREATE OR REPLACE FUNCTION fn_safety_observation_history() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO safety_observation_history (
        observation_id, segment_id, verification_state, confidence, evidence_hash
    ) VALUES (
        NEW.id, NEW.segment_id, NEW.verification_state, NEW.confidence, NEW.evidence_hash
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_safety_observation_history ON safety_observations;
CREATE TRIGGER trg_safety_observation_history
    AFTER INSERT OR UPDATE ON safety_observations
    FOR EACH ROW EXECUTE FUNCTION fn_safety_observation_history();

-- Anonymous reports (Phase 5 writes these; the evidence engine reads them).
-- description_redacted never leaves the API.
CREATE TABLE IF NOT EXISTS safety_reports (
    id                 BIGSERIAL PRIMARY KEY,
    segment_id         BIGINT NOT NULL REFERENCES road_segments(id) ON DELETE CASCADE,
    category           TEXT NOT NULL CHECK (category IN (
        'streetlight_not_working', 'poor_lighting', 'harassment', 'suspicious_activity',
        'blocked_sidewalk', 'unsafe_transport', 'road_hazard', 'other'
    )),
    description_redacted TEXT,
    reported_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    verification_state TEXT NOT NULL DEFAULT 'REPORTED' CHECK (
        verification_state IN ('VERIFIED', 'REPORTED', 'CORROBORATED', 'CONFLICTING', 'EXPIRED', 'REJECTED')
    ),
    confidence         REAL NOT NULL DEFAULT 0.5,
    client_hash        TEXT NOT NULL DEFAULT '',
    evidence_image_encrypted BYTEA,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Phase 5 columns for databases created before reports landed.
ALTER TABLE safety_reports ADD COLUMN IF NOT EXISTS client_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE safety_reports ADD COLUMN IF NOT EXISTS evidence_image_encrypted BYTEA;

CREATE INDEX IF NOT EXISTS idx_safety_reports_segment ON safety_reports (segment_id, category);

-- ---------------------------------------------------------------------------
-- Phase 8: admin audit log. Append-only; the admin key itself is never
-- stored — only its sha256 hash, for correlating repeated abuse.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id           BIGSERIAL PRIMARY KEY,
    action       TEXT NOT NULL,
    admin_hash   TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}',
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_action ON admin_audit_log (action, performed_at);