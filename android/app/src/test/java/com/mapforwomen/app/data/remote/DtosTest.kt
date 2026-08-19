package com.mapforwomen.app.data.remote

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Wire-format contract tests: the DTOs must parse real server payloads
 *  (schemas.py) and tolerate unknown fields. */
class DtosTest {

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true }

    @Test
    fun routesResponseParsesServerPayload() {
        val payload = """
            {
              "routes": [
                {
                  "route_type": "safety_priority",
                  "distance_m": 1234.5,
                  "duration_s": 900.0,
                  "risk_probability": 0.31,
                  "estimated_safety": 69,
                  "confidence": 0.87,
                  "uncertainty": 0.13,
                  "high_risk_fraction": 0.02,
                  "risk_exposure_m": 41.0,
                  "warnings": ["off the road network"],
                  "reasons": ["poor lighting on 12% of segments"],
                  "model_version": "deterministic-baseline-v1",
                  "segment_ids": [1, 2, 3],
                  "geometry": {"type": "LineString", "coordinates": [[77.209, 28.6139], [77.21, 28.614]]}
                }
              ]
            }
        """.trimIndent()
        val parsed = json.decodeFromString<RoutesResponseDto>(payload)
        val route = parsed.routes.first()
        assertEquals("safety_priority", route.routeType)
        assertEquals(1234.5, route.distanceM, 0.001)
        assertEquals(69, route.estimatedSafety)
        assertEquals("deterministic-baseline-v1", route.modelVersion)
        assertEquals(2, route.geometry.coordinates.size)
        assertEquals(listOf(1, 2, 3), route.segmentIds)
    }

    @Test
    fun modelsCurrentParsesGateClosedWithCvModels() {
        val payload = """
            {
              "risk_model": "deterministic-baseline-v1",
              "evidence_model": "evidence-baseline-v1",
              "dataset_versions": [],
              "ml_gate": {
                "open": false,
                "verified_observations": 12,
                "span_days": 3.2,
                "min_verified_observations": 1000,
                "min_span_days": 90
              },
              "cv_models": [
                {
                  "name": "base_model",
                  "version": "v1",
                  "kind": "cv_classifier",
                  "framework": "keras",
                  "checkpoint_path": "models/Base_model.h5",
                  "status": "VALIDATION_REQUIRED",
                  "metrics": {},
                  "integration": "not_integrated"
                }
              ]
            }
        """.trimIndent()
        val parsed = json.decodeFromString<ModelsCurrentResponseDto>(payload)
        assertFalse(parsed.mlGate.open)
        assertEquals(12, parsed.mlGate.verifiedObservations)
        assertEquals("VALIDATION_REQUIRED", parsed.cvModels.first().status)
    }

    @Test
    fun emergencySessionParsesServerPayload() {
        val payload = """
            {
              "session_id": "sess_abc",
              "status": "ACTIVE",
              "started_at": "2026-08-19T12:00:00+00:00",
              "ended_at": null,
              "end_reason": null,
              "latitude": 28.6139,
              "longitude": 77.2090,
              "last_known_at": null,
              "notified_contact_ids": [7],
              "notify_status": "PENDING",
              "location_sharing": null
            }
        """.trimIndent()
        val parsed = json.decodeFromString<EmergencySessionResponseDto>(payload)
        assertEquals("sess_abc", parsed.sessionId)
        assertEquals("ACTIVE", parsed.status)
        assertEquals(listOf(7), parsed.notifiedContactIds)
    }

    @Test
    fun deviceSessionParsesServerPayload() {
        val payload = """
            {"token": "tok_123", "client_id": "android-x", "expires_at": "2026-09-18T12:00:00+00:00"}
        """.trimIndent()
        val parsed = json.decodeFromString<DeviceSessionResponseDto>(payload)
        assertEquals("tok_123", parsed.token)
        assertEquals("android-x", parsed.clientId)
        assertTrue(parsed.expiresAt.startsWith("2026-09-18"))
    }

    @Test
    fun unknownFieldsAreIgnored() {
        val payload = """
            {"contacts": [{"id": 1, "name": "A", "phone": "+91", "extra_future_field": true}]}
        """.trimIndent()
        val parsed = json.decodeFromString<TrustedContactListResponseDto>(payload)
        assertEquals(1, parsed.contacts.size)
        assertEquals("A", parsed.contacts.first().name)
    }
}