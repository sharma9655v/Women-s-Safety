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

-- ---------------------------------------------------------------------------
-- Phase 9: personal safety features. All personal data is keyed by a
-- pseudonymous device-generated client_id (X-Client-Id header). No real
-- identity is ever stored. Phone numbers are encrypted at rest (Fernet).
-- Sessions self-expire; minimal retention by design.
-- ---------------------------------------------------------------------------

-- Trusted contacts (user-managed; never publicly exposed).
CREATE TABLE IF NOT EXISTS trusted_contacts (
    id           BIGSERIAL PRIMARY KEY,
    client_id    TEXT NOT NULL,
    name         TEXT NOT NULL,
    relationship TEXT NOT NULL DEFAULT 'friend',
    phone_encrypted BYTEA NOT NULL,
    role         TEXT NOT NULL DEFAULT 'secondary' CHECK (role IN ('primary', 'secondary')),
    enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trusted_contacts_client ON trusted_contacts (client_id);
CREATE INDEX IF NOT EXISTS idx_trusted_contacts_client_role
    ON trusted_contacts (client_id, role) WHERE enabled;

-- Emergency (SOS) sessions: created only after the client-side countdown
-- completes (cancel never reaches the backend). Location is last-known, never
-- a live stream without an explicit sharing session.
CREATE TABLE IF NOT EXISTS emergency_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ENDED', 'EXPIRED')),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at      TIMESTAMPTZ,
    end_reason    TEXT,
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    last_known_at TIMESTAMPTZ,
    notified_contact_ids JSONB NOT NULL DEFAULT '[]',
    notify_status TEXT NOT NULL DEFAULT 'no_channel'
        CHECK (notify_status IN ('no_channel', 'queued', 'sent', 'failed')),
    location_sharing UUID
);
CREATE INDEX IF NOT EXISTS idx_emergency_sessions_client
    ON emergency_sessions (client_id, status, started_at);

-- Explicit-consent live location sharing sessions (emergency or guardian).
-- Automatic expiry; never silent.
CREATE TABLE IF NOT EXISTS location_sharing_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('EMERGENCY', 'GUARDIAN')),
    owner_session UUID,
    status        TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'STOPPED', 'EXPIRED')),
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    stopped_at    TIMESTAMPTZ,
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    last_updated_at TIMESTAMPTZ,
    recipient_ids JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_sharing_sessions_client
    ON location_sharing_sessions (client_id, status, expires_at);

-- In-app notification events: every notification has a real source event.
-- channel 'app' is delivered via the in-app notification center; sms/telegram
-- require a configured provider (notify_channel setting). No fake delivery.
CREATE TABLE IF NOT EXISTS notification_events (
    id         BIGSERIAL PRIMARY KEY,
    client_id  TEXT NOT NULL,
    type       TEXT NOT NULL CHECK (type IN (
        'sos_started', 'sos_ended', 'location_sharing_started', 'location_sharing_stopped',
        'guardian_started', 'guardian_ended', 'journey_completed', 'checkin_reminder',
        'checkin_missed', 'checkin_escalated', 'route_changed', 'safety_alert'
    )),
    channel    TEXT NOT NULL DEFAULT 'app' CHECK (channel IN ('app', 'sms', 'telegram', 'none')),
    status     TEXT NOT NULL DEFAULT 'no_channel'
        CHECK (status IN ('no_channel', 'queued', 'sent', 'failed')),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notification_events_client
    ON notification_events (client_id, created_at DESC);

-- Guardian journeys: a trusted contact watches the journey. The owner checks
-- in periodically; a missed check-in escalates in stages (reminder ->
-- escalated notification; optionally auto-starting an emergency session when
-- guardian_auto_sos is enabled). Deviation from the planned route is detected
-- against the geometry provided at start (never from invented data).
CREATE TABLE IF NOT EXISTS guardian_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'ESCALATED')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    end_reason          TEXT,
    guardian_contact_ids JSONB NOT NULL DEFAULT '[]',
    expected_arrival_at TIMESTAMPTZ,
    planned_geometry    JSONB,
    checkin_grace_s     INTEGER NOT NULL DEFAULT 300,
    last_checkin_at     TIMESTAMPTZ,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    last_known_at       TIMESTAMPTZ,
    deviation_detected  BOOLEAN NOT NULL DEFAULT FALSE,
    first_deviation_at  TIMESTAMPTZ,
    escalation_stage    INTEGER NOT NULL DEFAULT 0,
    notified_stage      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_guardian_sessions_client
    ON guardian_sessions (client_id, status, started_at);

-- Community posts: anonymous, moderated updates. Status starts PENDING and an
-- admin may mark a post VERIFIED or REJECTED; the public feed shows only
-- VERIFIED and PENDING posts so no one mistakes unreviewed content for fact.
CREATE TABLE IF NOT EXISTS community_posts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('alert', 'route_update', 'photo')),
    location      TEXT NOT NULL,
    text          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'VERIFIED', 'REJECTED')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    moderated_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_community_posts_feed
    ON community_posts (status, created_at DESC);

-- ---------------------------------------------------------------------------
-- Journey Check-ins (Feature Group D): standalone safety check-ins outside
-- Guardian mode. User sets destination, expected arrival, interval, grace
-- period. Missed check-ins escalate in stages (reminder -> grace period ->
-- optional trusted contact notification). No auto-emergency.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journey_checkins (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED', 'ESCALATED', 'MISSED')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    end_reason          TEXT,
    destination_name    TEXT,
    destination_lat     DOUBLE PRECISION,
    destination_lon     DOUBLE PRECISION,
    expected_arrival_at TIMESTAMPTZ,
    checkin_interval_s  INTEGER NOT NULL DEFAULT 900,
    checkin_grace_s     INTEGER NOT NULL DEFAULT 300,
    last_checkin_at     TIMESTAMPTZ,
    next_checkin_at     TIMESTAMPTZ,
    contact_ids         JSONB NOT NULL DEFAULT '[]',
    escalation_stage    INTEGER NOT NULL DEFAULT 0,
    notified_stage      INTEGER NOT NULL DEFAULT 0,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    last_known_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_journey_checkins_client
    ON journey_checkins (client_id, status, started_at);

-- ---------------------------------------------------------------------------
-- Safety Alerts (Feature Group K): verified safety alerts from backend.
-- Categories: recent_verified_incident, lighting_issue, road_hazard,
-- blocked_sidewalk, route_obstruction, weather_hazard, emergency_event,
-- public_safety_notice.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS safety_alerts (
    id              BIGSERIAL PRIMARY KEY,
    category        TEXT NOT NULL CHECK (category IN (
        'recent_verified_incident', 'lighting_issue', 'road_hazard',
        'blocked_sidewalk', 'route_obstruction', 'weather_hazard',
        'emergency_event', 'public_safety_notice'
    )),
    severity        TEXT NOT NULL DEFAULT 'moderate' CHECK (severity IN ('low', 'moderate', 'high', 'critical')),
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    location_name   TEXT,
    description     TEXT,
    source          TEXT NOT NULL,
    evidence_status TEXT NOT NULL DEFAULT 'verified'
        CHECK (evidence_status IN ('verified', 'reported', 'unverified')),
    confidence      REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    observed_at     TIMESTAMPTZ NOT NULL,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_safety_alerts_geom ON safety_alerts (lat, lon);
CREATE INDEX IF NOT EXISTS idx_safety_alerts_category ON safety_alerts (category);
CREATE INDEX IF NOT EXISTS idx_safety_alerts_active ON safety_alerts (expires_at) WHERE expires_at > now();

-- ---------------------------------------------------------------------------
-- Personal Safety Preferences (Feature Group Q): user-configurable route
-- preferences that influence routing but never bypass the core safety model.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS safety_preferences (
    client_id                TEXT PRIMARY KEY,
    prefer_better_lit        BOOLEAN NOT NULL DEFAULT TRUE,
    prefer_main_roads        BOOLEAN NOT NULL DEFAULT TRUE,
    prefer_near_emergency    BOOLEAN NOT NULL DEFAULT TRUE,
    avoid_known_hazards      BOOLEAN NOT NULL DEFAULT TRUE,
    avoid_isolated_roads     BOOLEAN NOT NULL DEFAULT FALSE,
    minimize_walking_time    BOOLEAN NOT NULL DEFAULT FALSE,
    default_profile          TEXT NOT NULL DEFAULT 'balanced'
        CHECK (default_profile IN ('safety_priority', 'balanced', 'time_priority')),
    discreet_mode_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    voice_guidance_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    voice_language           TEXT NOT NULL DEFAULT 'en',
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Discreet Safety Mode (Feature Group S): settings for discreet access to
-- safety functions without visually obvious emergency screen.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS discreet_mode_settings (
    client_id            TEXT PRIMARY KEY,
    enabled              BOOLEAN NOT NULL DEFAULT FALSE,
    quick_sos_gesture    TEXT NOT NULL DEFAULT 'triple_tap',
    exit_to_neutral_app  BOOLEAN NOT NULL DEFAULT TRUE,
    neutral_app_label    TEXT NOT NULL DEFAULT 'Weather',
    neutral_app_icon     TEXT NOT NULL DEFAULT 'cloud-sun',
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Fake Call / Distraction Tool (Feature Group T): user-controlled local
-- utility for simulated incoming calls.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fake_call_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       TEXT NOT NULL,
    caller_name     TEXT NOT NULL DEFAULT 'Unknown',
    caller_number   TEXT,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    triggered_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'SCHEDULED'
        CHECK (status IN ('SCHEDULED', 'TRIGGERED', 'DISMISSED', 'EXPIRED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fake_call_sessions_client
    ON fake_call_sessions (client_id, status, scheduled_at);

-- ---------------------------------------------------------------------------
-- Voice Safety Assistance (Feature Group U): voice guidance settings and
-- session tracking.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS voice_guidance_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       TEXT NOT NULL,
    route_session_id UUID,
    language        TEXT NOT NULL DEFAULT 'en',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voice_guidance_client
    ON voice_guidance_sessions (client_id, active, started_at);
-- ---------------------------------------------------------------------------
-- Device session tokens (Group D auth): revocable bearer tokens bound to the
-- pseudonymous client_id. Only the sha256 hash of a token is stored.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_sessions (
    token_hash  TEXT PRIMARY KEY,
    client_id   TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_device_sessions_client
    ON device_sessions (client_id, expires_at);
