package com.mapforwomen.app.ui.screens

import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mapforwomen.app.data.SafetyRepository
import com.mapforwomen.app.location.TrackingService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Guardian journey screen: add trusted contacts and start/end a journey
 *  with periodic check-ins and location sharing to guardians. */
@Composable
fun GuardianScreen(repository: SafetyRepository, context: Context) {
    val scope = rememberCoroutineScope()
    var contacts by remember { mutableStateOf<List<com.mapforwomen.app.data.remote.TrustedContactDto>>(emptyList()) }
    var newName by remember { mutableStateOf("") }
    var newPhone by remember { mutableStateOf("") }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var sessionStatus by remember { mutableStateOf<String?>(null) }
    var lastCheckin by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }

    fun loadContacts() {
        scope.launch {
            try {
                contacts = withContext(Dispatchers.IO) { repository.contacts() }
                message = "${contacts.size} trusted contacts."
            } catch (exc: Exception) {
                message = exc.message
            }
        }
    }

    fun startJourney() {
        val guardianIds = contacts.filter { it.enabled }.map { it.id }
        if (guardianIds.isEmpty()) {
            message = "Add at least one trusted contact first."
            return
        }
        scope.launch {
            try {
                val session = withContext(Dispatchers.IO) {
                    repository.startGuardian(guardianIds, plannedGeometry = null)
                }
                sessionId = session.sessionId
                sessionStatus = session.status
                lastCheckin = session.lastCheckinAt
                val serviceIntent = Intent(context, TrackingService::class.java).apply {
                    action = Intent.ACTION_MAIN
                    putExtra(TrackingService.EXTRA_SESSION_ID, session.sessionId)
                    putExtra(TrackingService.EXTRA_KIND, TrackingService.KIND_GUARDIAN)
                    putExtra(TrackingService.EXTRA_LAT, 28.6139)
                    putExtra(TrackingService.EXTRA_LON, 77.2090)
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

    fun endJourney() {
        val id = sessionId ?: return
        scope.launch {
            try {
                withContext(Dispatchers.IO) { repository.endGuardian(id) }
                sessionId = null
                sessionStatus = null
                context.stopService(Intent(context, TrackingService::class.java))
            } catch (exc: Exception) {
                message = exc.message
            }
        }
    }

    fun checkIn() {
        val id = sessionId ?: return
        scope.launch {
            try {
                val session = withContext(Dispatchers.IO) { repository.guardianCheckin(id) }
                lastCheckin = session.lastCheckinAt
                message = "Check-in recorded."
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
        Text("Guardian journey", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Guardians get periodic check-ins and your live location until you arrive or cancel.",
            style = MaterialTheme.typography.bodyMedium,
        )

        sessionId?.let {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Active journey", style = MaterialTheme.typography.titleSmall)
                    Text("status: ${sessionStatus ?: "active"}")
                    lastCheckin?.let { checkin -> Text("last check-in: $checkin") }
                    Text("session: $it", style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        Button(
            onClick = { if (sessionId != null) endJourney() else startJourney() },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (sessionId != null) "End journey" else "Start guardian journey")
        }

        if (sessionId != null) {
            OutlinedButton(onClick = { checkIn() }, modifier = Modifier.fillMaxWidth()) {
                Text("Check in now")
            }
        }

        OutlinedButton(onClick = { loadContacts() }, modifier = Modifier.fillMaxWidth()) {
            Text("Refresh trusted contacts")
        }

        contacts.forEach { contact ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("${contact.name} (${contact.relationship})", style = MaterialTheme.typography.titleSmall)
                    Text("${contact.phone} · ${contact.role} · ${if (contact.enabled) "enabled" else "disabled"}")
                }
            }
        }

        TextField(
            value = newName,
            onValueChange = { newName = it },
            label = { Text("Contact name") },
            modifier = Modifier.fillMaxWidth(),
        )
        TextField(
            value = newPhone,
            onValueChange = { newPhone = it },
            label = { Text("Phone") },
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedButton(
            onClick = {
                if (newName.isBlank() || newPhone.isBlank()) {
                    message = "Name and phone are required."
                    return@OutlinedButton
                }
                scope.launch {
                    try {
                        withContext(Dispatchers.IO) { repository.addContact(newName, newPhone) }
                        newName = ""
                        newPhone = ""
                        loadContacts()
                    } catch (exc: Exception) {
                        message = exc.message
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Add trusted contact")
        }

        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Spacer(Modifier.height(4.dp))
    }
}