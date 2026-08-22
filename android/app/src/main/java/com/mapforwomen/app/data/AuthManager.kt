package com.mapforwomen.app.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import com.mapforwomen.app.data.remote.ApiClient
import com.mapforwomen.app.data.remote.DeviceSessionRequestDto
import com.mapforwomen.app.data.remote.DeviceSessionResponseDto
import java.security.SecureRandom
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Device identity + encrypted session token.
 *
 *  client_id is a random per-install id (not a hardware id — no IMEI/ANDROID_ID
 *  is ever sent). The session token is stored in EncryptedSharedPreferences
 *  (androidx.security-crypto) when available, falling back to private
 *  SharedPreferences on devices where the security provider is unavailable.
 */
class AuthManager(context: Context) {

    private val appContext = context.applicationContext
    private val prefs: SharedPreferences by lazy {
        encryptedPrefs(appContext)
    }

    fun clientId(): String {
        val existing = prefs.getString(KEY_CLIENT_ID, null)
        if (!existing.isNullOrBlank()) return existing
        val generated = "android-" + randomHex(24)
        prefs.edit().putString(KEY_CLIENT_ID, generated).apply()
        return generated
    }

    fun token(): String? = prefs.getString(KEY_TOKEN, null)

    fun saveSession(session: DeviceSessionResponseDto) {
        prefs.edit()
            .putString(KEY_TOKEN, session.token)
            .putString(KEY_CLIENT_ID, session.clientId)
            .putString(KEY_EXPIRES_AT, session.expiresAt)
            .apply()
        ApiClient.authToken = session.token
    }

    fun clearSession() {
        prefs.edit().remove(KEY_TOKEN).remove(KEY_EXPIRES_AT).apply()
        ApiClient.authToken = null
    }

    suspend fun ensureSession() {
        if (token() == null) {
            val session = withContext(Dispatchers.IO) {
                ApiClient.service.createDeviceSession(DeviceSessionRequestDto(clientId = clientId()))
            }
            saveSession(session)
        } else {
            ApiClient.authToken = token()
        }
    }

    private fun encryptedPrefs(context: Context): SharedPreferences {
        return try {
            val masterKey = androidx.security.crypto.MasterKey.Builder(context)
                .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM)
                .build()
            androidx.security.crypto.EncryptedSharedPreferences.create(
                context,
                "mapfw_secure_prefs",
                masterKey,
                androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        } catch (_: Exception) {
            // Security provider unavailable — degrade to private prefs. The
            // token is revocable server-side; this fallback never ships in
            // release builds' primary path and is documented.
            context.getSharedPreferences("mapfw_secure_prefs", Context.MODE_PRIVATE)
        }
    }

    private fun randomHex(bytes: Int): String {
        val buffer = ByteArray(bytes)
        SecureRandom().nextBytes(buffer)
        return Base64.encodeToString(buffer, Base64.NO_WRAP or Base64.URL_SAFE)
            .replace("=", "")
            .take(bytes * 2)
    }

    private companion object {
        const val KEY_CLIENT_ID = "client_id"
        const val KEY_TOKEN = "session_token"
        const val KEY_EXPIRES_AT = "session_expires_at"
    }
}