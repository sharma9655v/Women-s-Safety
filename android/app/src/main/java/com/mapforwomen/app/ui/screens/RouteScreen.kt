package com.mapforwomen.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import com.mapforwomen.app.data.remote.LatLonDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Route planning screen: pick origin/destination (geocoded or manual),
 *  request the three ranked route types and show them honestly. */
@Composable
fun RouteScreen(repository: SafetyRepository) {
    var originQuery by remember { mutableStateOf("Connaught Place, Delhi") }
    var destinationQuery by remember { mutableStateOf("India Gate, Delhi") }
    var origin by remember { mutableStateOf<LatLonDto?>(LatLonDto(28.6315, 77.2167)) }
    var destination by remember { mutableStateOf<LatLonDto?>(LatLonDto(28.6129, 77.2295)) }
    var safetyPreference by remember { mutableStateOf("safety_priority") }
    var hour by remember { mutableStateOf(21) }
    var loading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var routes by remember { mutableStateOf<List<com.mapforwomen.app.data.remote.RouteResultDto>>(emptyList()) }
    val scope = rememberCoroutineScope()

    fun geocode(query: String, setter: (LatLonDto) -> Unit) {
        scope.launch {
            try {
                val results = withContext(Dispatchers.IO) { repository.geocode(query) }
                results.firstOrNull()?.let { setter(LatLonDto(it.lat, it.lon)) }
                    ?: run { message = "No geocode result for \"$query\"." }
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
        Text("Plan a route", style = MaterialTheme.typography.headlineSmall)

        TextField(
            value = originQuery,
            onValueChange = { originQuery = it },
            label = { Text("From") },
            modifier = Modifier.fillMaxWidth(),
        )
        Row {
            OutlinedButton(onClick = { geocode(originQuery) { origin = it } }) { Text("Geocode") }
            Spacer(Modifier.weight(1f))
            Text("${"%.4f".format(origin?.lat ?: 0.0)}, ${"%.4f".format(origin?.lon ?: 0.0)}")
        }

        TextField(
            value = destinationQuery,
            onValueChange = { destinationQuery = it },
            label = { Text("To") },
            modifier = Modifier.fillMaxWidth(),
        )
        Row {
            OutlinedButton(onClick = { geocode(destinationQuery) { destination = it } }) { Text("Geocode") }
            Spacer(Modifier.weight(1f))
            Text("${"%.4f".format(destination?.lat ?: 0.0)}, ${"%.4f".format(destination?.lon ?: 0.0)}")
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { safetyPreference = "safety_priority" }) {
                Text(if (safetyPreference == "safety_priority") "Safest ✓" else "Safest")
            }
            OutlinedButton(onClick = { safetyPreference = "balanced" }) {
                Text(if (safetyPreference == "balanced") "Balanced ✓" else "Balanced")
            }
            OutlinedButton(onClick = { hour = (hour + 1) % 24 }) { Text("Hour: $hour") }
        }

        Button(
            onClick = {
                val from = origin ?: return@Button
                val to = destination ?: return@Button
                loading = true
                message = null
                scope.launch {
                    try {
                        val result = withContext(Dispatchers.IO) {
                            repository.routes(from, to, hourIst = hour, safetyPreference = safetyPreference)
                        }
                        routes = result.routes
                        if (routes.isEmpty()) message = "No route returned."
                    } catch (exc: Exception) {
                        message = exc.message
                    } finally {
                        loading = false
                    }
                }
            },
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (loading) "Planning…" else "Plan route")
        }

        routes.forEach { route ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(route.routeType.replace("_", " ").replaceFirstChar { it.uppercase() },
                        style = MaterialTheme.typography.titleSmall)
                    Text("distance ${"%.0f".format(route.distanceM)} m · ${"%.0f".format(route.durationS / 60)} min")
                    Text("estimated safety ${route.estimatedSafety}/100 · risk ${"%.0f".format(route.riskProbability * 100)}%")
                    Text("confidence ${"%.0f".format(route.confidence * 100)}% · uncertainty ${"%.0f".format(route.uncertainty * 100)}%")
                    Text("model ${route.modelVersion}", style = MaterialTheme.typography.bodySmall)
                    route.reasons.forEach { reason -> Text("• $reason", style = MaterialTheme.typography.bodySmall) }
                }
            }
        }

        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Spacer(Modifier.height(4.dp))
    }
}