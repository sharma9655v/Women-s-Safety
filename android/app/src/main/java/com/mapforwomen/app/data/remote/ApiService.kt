package com.mapforwomen.app.data.remote

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

/** Retrofit interface mirroring the verified API surface of the server. */
interface ApiService {

    // --- auth -------------------------------------------------------------

    @POST("api/auth/device")
    suspend fun createDeviceSession(
        @Body body: DeviceSessionRequestDto,
    ): DeviceSessionResponseDto

    // --- routing ------------------------------------------------------------

    @POST("api/routes")
    suspend fun getRoutes(
        @Body body: RouteRequestDto,
    ): RoutesResponseDto

    // --- reports -------------------------------------------------------------

    @POST("api/reports")
    suspend fun createReport(
        @Body body: ReportRequestDto,
    ): ReportResponseDto

    // --- trusted contacts ------------------------------------------------------

    @GET("api/contacts")
    suspend fun listContacts(): TrustedContactListResponseDto

    @POST("api/contacts")
    suspend fun createContact(
        @Body body: TrustedContactInputDto,
    ): TrustedContactDto

    @PUT("api/contacts/{contactId}")
    suspend fun updateContact(
        @Path("contactId") contactId: Int,
        @Body body: TrustedContactInputDto,
    ): TrustedContactDto

    @DELETE("api/contacts/{contactId}")
    suspend fun deleteContact(
        @Path("contactId") contactId: Int,
    ): retrofit2.Response<Unit>

    // --- emergency -------------------------------------------------------------

    @POST("api/emergency/sessions")
    suspend fun startEmergency(
        @Body body: EmergencyCreateRequestDto,
    ): EmergencySessionResponseDto

    @GET("api/emergency/sessions/active")
    suspend fun activeEmergency(): EmergencySessionResponseDto?

    @POST("api/emergency/sessions/{sessionId}/location")
    suspend fun updateEmergencyLocation(
        @Path("sessionId") sessionId: String,
        @Body body: SharingLocationUpdateDto,
    ): EmergencySessionResponseDto

    @POST("api/emergency/sessions/{sessionId}/end")
    suspend fun endEmergency(
        @Path("sessionId") sessionId: String,
        @Body body: EmergencyEndRequestDto,
    ): EmergencyEndResponseDto

    // --- guardian ---------------------------------------------------------------

    @POST("api/guardian/sessions")
    suspend fun startGuardian(
        @Body body: GuardianCreateRequestDto,
    ): GuardianSessionResponseDto

    @GET("api/guardian/sessions/active")
    suspend fun activeGuardian(): GuardianSessionResponseDto?

    @POST("api/guardian/sessions/{sessionId}/location")
    suspend fun updateGuardianLocation(
        @Path("sessionId") sessionId: String,
        @Body body: SharingLocationUpdateDto,
    ): GuardianSessionResponseDto

    @POST("api/guardian/sessions/{sessionId}/checkin")
    suspend fun guardianCheckin(
        @Path("sessionId") sessionId: String,
    ): GuardianSessionResponseDto

    @POST("api/guardian/sessions/{sessionId}/end")
    suspend fun endGuardian(
        @Path("sessionId") sessionId: String,
        @Body body: GuardianEndRequestDto,
    ): GuardianEndResponseDto

    // --- model status / geocode ------------------------------------------------

    @GET("api/models/current")
    suspend fun modelsCurrent(): ModelsCurrentResponseDto

    @GET("api/geocode")
    suspend fun geocode(
        @Query("q") query: String,
    ): GeocodeResponseDto
}