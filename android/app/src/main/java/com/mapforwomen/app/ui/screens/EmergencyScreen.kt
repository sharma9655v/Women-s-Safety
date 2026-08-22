package com.mapforwomen.app.ui.screens

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mapforwomen.app.data.SafetyRepository
import com.mapforwomen.app.location.TrackingService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Emergency screen: 5-second countdown before an SOS session starts
 *  (a cancel never reaches the backend), then a foreground tracking service
 *  pushes location updates until the user ends the session. */
@Composable
fun EmergencyScreen(repository: SafetyRepository, context: Context) {
    val scope = rememberCoroutineScope()
    var sessionId by remember { mutableStateOf<String?>(null) }
    var sessionStatus by remember { mutableStateOf<String?>(null) }
    var countingDown by remember { mutableStateOf(false) }
    var countdown by remember { mutableLongStateOf(0L) }
    var message by remember { mutableStateOf<String?>(null) }
    var contacts by remember { mutableStateOf<List<com.mapforwomen.app.data.remote.TrustedContactDto>>(emptyList()) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) message = "Location permission required for SOS."
    }

    fun lastKnownLocation(): Pair<Double, Double> {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val hasPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        return if (hasPermission) {
            val location = manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                ?: manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            if (location != null) location.latitude to location.longitude else 28.6139 to 77.2090
        } else {
            28.6139 to 77.2090
        }
    }

    fun startSos() {
        val (lat, lon) = lastKnownLocation()
        val contactIds = contacts.filter { it.enabled }.map { it.id }
        scope.launch {
            try {
                val session = withContext(Dispatchers.IO) {
                    repository.startEmergency(lat, lon, contactIds)
                }
                sessionId = session.sessionId
                sessionStatus = session.status
                val serviceIntent = Intent(context, TrackingService::class.java).apply {
                    action = Intent.ACTION_MAIN
                    putExtra(TrackingService.EXTRA_SESSION_ID, session.sessionId)
                    putExtra(TrackingService.EXTRA_KIND, TrackingService.KIND_EMERGENCY)
                    putExtra(TrackingService.EXTRA_LAT, lat)
                    putExtra(TrackingService.EXTRA_LON, lon)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
            } catch (exc: Exception) {
                message = exc.message
            }
        }
    }

    fun endSos() {
        val id = sessionId ?: return
        scope.launch {
            try {
                withContext(Dispatchers.IO) { repository.endEmergency(id) }
                sessionId = null
                sessionStatus = null
                context.stopService(Intent(context, TrackingService::class.java))
            } catch (exc: Exception) {
                message = exc.message
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Emergency SOS", style = MaterialTheme.typography.headlineSmall)
        Text(
            "An emergency session notifies your trusted contacts and shares your live location until you end it.",
            style = MaterialTheme.typography.bodyMedium,
        )

        if (countingDown) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(
                    "SOS in $countdown… tap Cancel to stop.",
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.titleMedium,
                )
            }
        }

        sessionId?.let {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Active SOS session", style = MaterialTheme.typography.titleSmall)
                    Text("status: ${sessionStatus ?: "active"}")
                    Text("session: $it", style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        Button(
            onClick = {
                if (sessionId != null) {
                    endSos()
                } else {
                    permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                    countingDown = true
                    countdown = 5
                    scope.launch {
                        repeat(4) {
                            delay(1000)
                            if (!countingDown) return@launch
                            countdown -= 1
                        }
                        if (!countingDown) return@launch
                        countingDown = false
                        startSos()
                    }
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (sessionId != null) "End SOS session" else "Start SOS (5 s countdown)")
        }

        if (countingDown) {
            OutlinedButton(
                onClick = {
                    countingDown = false
                    countdown = 0
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Cancel")
            }
        }

        OutlinedButton(
            onClick = {
                scope.launch {
                    try {
                        contacts = withContext(Dispatchers.IO) { repository.contacts() }
                        message = "${contacts.size} trusted contacts loaded."
                    } catch (exc: Exception) {
                        message = exc.message
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Load trusted contacts")
        }

        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Spacer(Modifier.height(4.dp))
    }
}