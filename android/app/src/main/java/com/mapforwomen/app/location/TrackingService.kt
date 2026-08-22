package com.mapforwomen.app.location

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.mapforwomen.app.MainActivity
import com.mapforwomen.app.R
import com.mapforwomen.app.data.SafetyRepository
import com.mapforwomen.app.data.RepositoryException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/** Foreground location service.
 *
 *  Responsibilities:
 *   - keep a lightweight foreground notification (privacy: the service is
 *     visible — no stealth background tracking),
 *   - when an emergency or guardian session is running, push location
 *     updates to the API on a bounded interval,
 *   - self-stops when the session ends (bounded lifetime by design).
 *
 *  Honesty rule: the service only ever reports the last known location that
 *  the user's own session requested; it never performs background
 *  surveillance-style tracking beyond the active session.
 */
class TrackingService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var locationJob: Job? = null
    private var sessionId: String? = null
    private var kind: String = KIND_EMERGENCY
    private var lastLatitude: Double = 0.0
    private var lastLongitude: Double = 0.0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        sessionId = intent?.getStringExtra(EXTRA_SESSION_ID)
        kind = intent?.getStringExtra(EXTRA_KIND) ?: KIND_EMERGENCY
        lastLatitude = intent?.getDoubleExtra(EXTRA_LAT, 0.0) ?: 0.0
        lastLongitude = intent?.getDoubleExtra(EXTRA_LON, 0.0) ?: 0.0
        val notification = buildNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
        startTrackingLoop()
        return START_STICKY
    }

    override fun onDestroy() {
        locationJob?.cancel()
        scope.cancel()
        super.onDestroy()
    }

    private fun startTrackingLoop() {
        locationJob?.cancel()
        locationJob = scope.launch {
            val repository = (application as com.mapforwomen.app.MapForWomenApp).repository
            var ticks = 0
            while (isActive) {
                if (ticks % 6 == 0 && hasFineLocation()) {
                    pushLatestLocation(repository)
                }
                ticks += 1
                delay(10_000L) // bounded 10s cadence; the API rate-limits anyway
            }
        }
    }

    private suspend fun pushLatestLocation(repository: SafetyRepository) {
        val session = sessionId ?: return
        // Report the freshest fix the platform exposes (last-known GPS fix;
        // no continuous background GPS subscription beyond the session).
        freshFix()?.let { (lat, lon) ->
            lastLatitude = lat
            lastLongitude = lon
        }
        try {
            when (kind) {
                KIND_EMERGENCY ->
                    repository.updateEmergencyLocation(session, lastLatitude, lastLongitude)
                KIND_GUARDIAN ->
                    repository.updateGuardianLocation(session, lastLatitude, lastLongitude)
            }
        } catch (_: RepositoryException) {
            // transient failure; the loop retries on the next tick
        }
    }

    private fun freshFix(): Pair<Double, Double>? {
        if (!hasFineLocation()) return null
        val manager = getSystemService(LOCATION_SERVICE) as LocationManager
        return try {
            val fix = manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                ?: manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            if (fix != null) fix.latitude to fix.longitude else null
        } catch (_: SecurityException) {
            null
        }
    }

    private fun hasFineLocation(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED

    private fun buildNotification(): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, TrackingService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.tracking_notification_title))
            .setContentText(getString(R.string.tracking_notification_text))
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setOngoing(true)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.tracking_notification_stop), stopIntent)
            .build()
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.tracking_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        )
        getSystemService(NotificationManager::class.java)?.createNotificationChannel(channel)
    }

    companion object {
        const val KIND_EMERGENCY = "emergency"
        const val KIND_GUARDIAN = "guardian"
        const val ACTION_STOP = "com.mapforwomen.app.action.STOP_TRACKING"
        const val EXTRA_SESSION_ID = "session_id"
        const val EXTRA_KIND = "kind"
        const val EXTRA_LAT = "latitude"
        const val EXTRA_LON = "longitude"

        private const val CHANNEL_ID = "tracking"
        private const val NOTIFICATION_ID = 42
    }
}