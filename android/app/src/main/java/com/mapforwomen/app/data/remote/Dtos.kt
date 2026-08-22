package com.mapforwomen.app.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Wire DTOs matching the Map for Women API schemas (apps/api/app/schemas.py). */

@Serializable
data class LatLonDto(
    val lat: Double,
    val lon: Double,
)

@Serializable
data class RouteRequestDto(
    val origin: LatLonDto,
    val destination: LatLonDto,
    val mode: String = "walking",
    @SerialName("safety_preference") val safetyPreference: String = "balanced",
    @SerialName("hour_ist") val hourIst: Int? = null,
)

@Serializable
data class RouteGeometryDto(
    val type: String = "LineString",
    val coordinates: List<List<Double>> = emptyList(),
)

@Serializable
data class RouteResultDto(
    @SerialName("route_type") val routeType: String,
    @SerialName("distance_m") val distanceM: Double = 0.0,
    @SerialName("duration_s") val durationS: Double = 0.0,
    @SerialName("risk_probability") val riskProbability: Double = 0.0,
    @SerialName("estimated_safety") val estimatedSafety: Int = 0,
    val confidence: Double = 0.0,
    val uncertainty: Double = 0.0,
    @SerialName("high_risk_fraction") val highRiskFraction: Double = 0.0,
    @SerialName("risk_exposure_m") val riskExposureM: Double = 0.0,
    val warnings: List<String> = emptyList(),
    val reasons: List<String> = emptyList(),
    @SerialName("model_version") val modelVersion: String = "",
    @SerialName("segment_ids") val segmentIds: List<Int> = emptyList(),
    val geometry: RouteGeometryDto = RouteGeometryDto(),
)

@Serializable
data class RoutesResponseDto(
    val routes: List<RouteResultDto> = emptyList(),
)

@Serializable
data class ReportRequestDto(
    @SerialName("segment_id") val segmentId: Int,
    val category: String,
    val description: String? = null,
    @SerialName("evidence_image") val evidenceImage: String? = null,
)

@Serializable
data class ReportResponseDto(
    @SerialName("report_id") val reportId: Int,
    @SerialName("segment_id") val segmentId: Int,
    val category: String,
    @SerialName("verification_state") val verificationState: String,
    @SerialName("model_version") val modelVersion: String,
)

@Serializable
data class DeviceSessionRequestDto(
    @SerialName("client_id") val clientId: String,
)

@Serializable
data class DeviceSessionResponseDto(
    val token: String,
    @SerialName("client_id") val clientId: String,
    @SerialName("expires_at") val expiresAt: String,
)

@Serializable
data class EmergencyCreateRequestDto(
    val latitude: Double,
    val longitude: Double,
    @SerialName("notified_contact_ids") val notifiedContactIds: List<Int> = emptyList(),
)

@Serializable
data class EmergencySessionResponseDto(
    @SerialName("session_id") val sessionId: String,
    val status: String,
    @SerialName("started_at") val startedAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("end_reason") val endReason: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("last_known_at") val lastKnownAt: String? = null,
    @SerialName("notified_contact_ids") val notifiedContactIds: List<Int> = emptyList(),
    @SerialName("notify_status") val notifyStatus: String = "",
    @SerialName("location_sharing") val locationSharing: String? = null,
)

@Serializable
data class EmergencyEndRequestDto(
    val reason: String = "ended_by_user",
)

@Serializable
data class EmergencyEndResponseDto(
    @SerialName("session_id") val sessionId: String,
    val status: String,
    @SerialName("ended_at") val endedAt: String,
    @SerialName("end_reason") val endReason: String,
)

@Serializable
data class SharingLocationUpdateDto(
    val latitude: Double,
    val longitude: Double,
)

@Serializable
data class TrustedContactDto(
    val id: Int,
    val name: String,
    val relationship: String = "",
    val phone: String = "",
    val role: String = "secondary",
    val enabled: Boolean = true,
)

@Serializable
data class TrustedContactListResponseDto(
    val contacts: List<TrustedContactDto> = emptyList(),
)

@Serializable
data class TrustedContactInputDto(
    val name: String,
    val relationship: String = "friend",
    val phone: String,
    val role: String = "secondary",
)

@Serializable
data class GuardianCreateRequestDto(
    @SerialName("guardian_contact_ids") val guardianContactIds: List<Int> = emptyList(),
    @SerialName("expected_arrival_at") val expectedArrivalAt: String? = null,
    @SerialName("planned_geometry") val plannedGeometry: List<List<Double>>? = null,
    @SerialName("checkin_grace_s") val checkinGraceS: Int = 300,
)

@Serializable
data class GuardianSessionResponseDto(
    @SerialName("session_id") val sessionId: String,
    val status: String,
    @SerialName("started_at") val startedAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("end_reason") val endReason: String? = null,
    @SerialName("guardian_contact_ids") val guardianContactIds: List<Int> = emptyList(),
    @SerialName("expected_arrival_at") val expectedArrivalAt: String? = null,
    @SerialName("checkin_deadline") val checkinDeadline: String = "",
    @SerialName("checkin_grace_s") val checkinGraceS: Int = 300,
    @SerialName("last_checkin_at") val lastCheckinAt: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("last_known_at") val lastKnownAt: String? = null,
    @SerialName("deviation_detected") val deviationDetected: Boolean = false,
    @SerialName("first_deviation_at") val firstDeviationAt: String? = null,
    @SerialName("escalation_stage") val escalationStage: Int = 0,
)

@Serializable
data class GuardianEndRequestDto(
    val reason: String = "arrived",
)

@Serializable
data class GuardianEndResponseDto(
    @SerialName("session_id") val sessionId: String,
    val status: String,
    @SerialName("ended_at") val endedAt: String,
    @SerialName("end_reason") val endReason: String,
)

@Serializable
data class MlGateDto(
    val open: Boolean = false,
    @SerialName("verified_observations") val verifiedObservations: Int = 0,
    @SerialName("span_days") val spanDays: Double? = null,
    @SerialName("min_verified_observations") val minVerifiedObservations: Int = 1000,
    @SerialName("min_span_days") val minSpanDays: Int = 90,
)

@Serializable
data class CvModelInfoDto(
    val name: String = "",
    val version: String = "",
    val kind: String = "",
    val framework: String = "",
    @SerialName("checkpoint_path") val checkpointPath: String = "",
    val status: String = "",
    val metrics: Map<String, Double> = emptyMap(),
    val integration: String = "not_integrated",
)

@Serializable
data class ModelsCurrentResponseDto(
    @SerialName("risk_model") val riskModel: String = "",
    @SerialName("evidence_model") val evidenceModel: String = "",
    @SerialName("dataset_versions") val datasetVersions: List<String> = emptyList(),
    @SerialName("ml_gate") val mlGate: MlGateDto = MlGateDto(),
    @SerialName("cv_models") val cvModels: List<CvModelInfoDto> = emptyList(),
)

@Serializable
data class GeocodeResultDto(
    val name: String,
    val kind: String = "",
    val type: String? = null,
    val lat: Double,
    val lon: Double,
)

@Serializable
data class GeocodeResponseDto(
    val results: List<GeocodeResultDto> = emptyList(),
)