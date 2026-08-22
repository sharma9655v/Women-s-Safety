package com.mapforwomen.app.data

import com.mapforwomen.app.data.remote.ApiClient
import com.mapforwomen.app.data.remote.EmergencyCreateRequestDto
import com.mapforwomen.app.data.remote.EmergencyEndRequestDto
import com.mapforwomen.app.data.remote.EmergencyEndResponseDto
import com.mapforwomen.app.data.remote.EmergencySessionResponseDto
import com.mapforwomen.app.data.remote.GuardianCreateRequestDto
import com.mapforwomen.app.data.remote.GuardianEndRequestDto
import com.mapforwomen.app.data.remote.GuardianEndResponseDto
import com.mapforwomen.app.data.remote.GuardianSessionResponseDto
import com.mapforwomen.app.data.remote.LatLonDto
import com.mapforwomen.app.data.remote.ModelsCurrentResponseDto
import com.mapforwomen.app.data.remote.ReportRequestDto
import com.mapforwomen.app.data.remote.ReportResponseDto
import com.mapforwomen.app.data.remote.RouteRequestDto
import com.mapforwomen.app.data.remote.RoutesResponseDto
import com.mapforwomen.app.data.remote.SharingLocationUpdateDto
import com.mapforwomen.app.data.remote.TrustedContactDto
import com.mapforwomen.app.data.remote.TrustedContactInputDto
import com.mapforwomen.app.data.remote.TrustedContactListResponseDto
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Single entry point for app -> API calls. All calls run on Dispatchers.IO
 *  and surface typed [RepositoryException] instead of raw network errors. */
class SafetyRepository(private val auth: AuthManager) {

    suspend fun routes(
        origin: LatLonDto,
        destination: LatLonDto,
        hourIst: Int? = null,
        safetyPreference: String = "balanced",
    ): RoutesResponseDto = api {
        ApiClient.service.getRoutes(
            RouteRequestDto(
                origin = origin,
                destination = destination,
                mode = "walking",
                safetyPreference = safetyPreference,
                hourIst = hourIst,
            )
        )
    }

    suspend fun models(): ModelsCurrentResponseDto = api {
        ApiClient.service.modelsCurrent()
    }

    suspend fun geocode(query: String): List<com.mapforwomen.app.data.remote.GeocodeResultDto> = api {
        ApiClient.service.geocode(query).results
    }

    suspend fun report(
        segmentId: Int,
        category: String,
        description: String? = null,
    ): ReportResponseDto = api {
        ApiClient.service.createReport(
            ReportRequestDto(
                segmentId = segmentId,
                category = category,
                description = description,
            )
        )
    }

    suspend fun contacts(): List<TrustedContactDto> = api {
        ApiClient.service.listContacts().contacts
    }

    suspend fun addContact(name: String, phone: String, relationship: String = "friend"): TrustedContactDto =
        api {
            ApiClient.service.createContact(
                TrustedContactInputDto(name = name, phone = phone, relationship = relationship)
            )
        }

    suspend fun startEmergency(
        latitude: Double,
        longitude: Double,
        contactIds: List<Int>,
    ): EmergencySessionResponseDto = api {
        ApiClient.service.startEmergency(
            EmergencyCreateRequestDto(
                latitude = latitude,
                longitude = longitude,
                notifiedContactIds = contactIds,
            )
        )
    }

    suspend fun endEmergency(sessionId: String): EmergencyEndResponseDto = api {
        ApiClient.service.endEmergency(sessionId, EmergencyEndRequestDto())
    }

    suspend fun updateEmergencyLocation(
        sessionId: String,
        latitude: Double,
        longitude: Double,
    ): EmergencySessionResponseDto = api {
        ApiClient.service.updateEmergencyLocation(
            sessionId,
            SharingLocationUpdateDto(latitude = latitude, longitude = longitude),
        )
    }

    suspend fun startGuardian(
        contactIds: List<Int>,
        plannedGeometry: List<List<Double>>? = null,
    ): GuardianSessionResponseDto = api {
        ApiClient.service.startGuardian(
            GuardianCreateRequestDto(
                guardianContactIds = contactIds,
                plannedGeometry = plannedGeometry,
            )
        )
    }

    suspend fun updateGuardianLocation(
        sessionId: String,
        latitude: Double,
        longitude: Double,
    ): GuardianSessionResponseDto = api {
        ApiClient.service.updateGuardianLocation(
            sessionId,
            SharingLocationUpdateDto(latitude = latitude, longitude = longitude),
        )
    }

    suspend fun endGuardian(sessionId: String): GuardianEndResponseDto = api {
        ApiClient.service.endGuardian(sessionId, GuardianEndRequestDto())
    }

    suspend fun guardianCheckin(sessionId: String): GuardianSessionResponseDto = api {
        ApiClient.service.guardianCheckin(sessionId)
    }

    private suspend fun <T> api(block: suspend () -> T): T = withContext(Dispatchers.IO) {
        auth.ensureSession()
        try {
            block()
        } catch (exc: IOException) {
            throw RepositoryException("Network error: ${exc.message}", exc)
        } catch (exc: retrofit2.HttpException) {
            throw RepositoryException("Server error (HTTP ${exc.code()})", exc)
        }
    }
}

class RepositoryException(message: String, cause: Throwable? = null) :
    Exception(message, cause)