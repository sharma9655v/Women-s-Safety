package com.mapforwomen.app.ui.screens

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.mapforwomen.app.data.SafetyRepository
import com.mapforwomen.app.data.remote.LatLonDto
import com.mapforwomen.app.data.remote.RouteResultDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Polyline

private val DELHI_CENTER = GeoPoint(28.6139, 77.2090)

@Composable
fun HomeScreen(
    repository: SafetyRepository,
    onOpenRoute: () -> Unit,
    onOpenReport: () -> Unit,
) {
    val context = LocalContext.current
    var mapView by remember { mutableStateOf<MapView?>(null) }
    var route by remember { mutableStateOf<RouteResultDto?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var lastLocation by remember { mutableStateOf(DELHI_CENTER) }

    val locationPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) message = "Location permission denied; using demo location."
    }
    LaunchedEffect(Unit) {
        locationPermission.launch(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    fun drawRoute(routeResult: RouteResultDto) {
        val view = mapView ?: return
        val stale = view.overlays.filterIsInstance<Polyline>()
        stale.forEach { view.overlays.remove(it) }
        val points = routeResult.geometry.coordinates.map { (lon, lat) -> GeoPoint(lat, lon) }
        if (points.size >= 2) {
            val line = Polyline(view).apply {
                setPoints(points)
                outlinePaint.color = 0xFF7B1FA2.toInt()
                outlinePaint.strokeWidth = 6f
            }
            view.overlays.add(line)
            view.invalidate()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "Route is an estimate, never a guarantee.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(12.dp),
            )
        }

        AndroidView(
            factory = { ctx ->
                MapView(ctx).apply {
                    setTileSource(org.osmdroid.tileprovider.tilesource.TileSourceFactory.MAPNIK)
                    setMultiTouchControls(true)
                    controller.setZoom(15.0)
                    controller.setCenter(DELHI_CENTER)
                    mapView = this
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(380.dp),
        )

        var loading by remember { mutableStateOf(false) }
        var safetyPreference by remember { mutableStateOf("balanced") }
        var hour by remember { mutableStateOf(21) }
        val scope = rememberCoroutineScope()

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { safetyPreference = "balanced" }) {
                Text(if (safetyPreference == "balanced") "Balanced ✓" else "Balanced")
            }
            OutlinedButton(onClick = { safetyPreference = "safety_priority" }) {
                Text(if (safetyPreference == "safety_priority") "Safest ✓" else "Safest")
            }
            OutlinedButton(onClick = { hour = (hour + 1) % 24 }) { Text("Hour: $hour") }
        }

        Button(
            onClick = {
                loading = true
                message = null
                scope.launch {
                    try {
                        val result = withContext(Dispatchers.IO) {
                            repository.routes(
                                origin = LatLonDto(lastLocation.latitude, lastLocation.longitude),
                                destination = LatLonDto(28.6315, 77.2167),
                                hourIst = hour,
                                safetyPreference = safetyPreference,
                            )
                        }
                        val best = result.routes.firstOrNull()
                        route = best
                        if (best != null) drawRoute(best) else message = "No route returned."
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
            Text(if (loading) "Planning…" else "Plan safest route")
        }

        route?.let { best ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Safety-priority route", style = MaterialTheme.typography.titleSmall)
                    Text("distance ${"%.0f".format(best.distanceM)} m · ${"%.0f".format(best.durationS / 60)} min")
                    Text("estimated safety ${best.estimatedSafety}/100 · risk ${"%.0f".format(best.riskProbability * 100)}%")
                    Text("confidence ${"%.0f".format(best.confidence * 100)}% · uncertainty ${"%.0f".format(best.uncertainty * 100)}%")
                    best.reasons.forEach { reason ->
                        Text("• $reason", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }

        message?.let {
            Text(it, color = MaterialTheme.colorScheme.error)
        }

        Spacer(Modifier.height(4.dp))
        Row {
            OutlinedButton(onClick = onOpenRoute) { Text("Plan custom route") }
            Spacer(Modifier.width(8.dp))
            OutlinedButton(onClick = onOpenReport) { Text("Report incident") }
            Spacer(Modifier.width(8.dp))
            OutlinedButton(
                onClick = {
                    val newLocation = GeoPoint(
                        lastLocation.latitude + 0.001,
                        lastLocation.longitude + 0.001,
                    )
                    lastLocation = newLocation
                    mapView?.controller?.setCenter(newLocation)
                }
            ) { Text("Simulate next position") }
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            mapView?.onDetach()
        }
    }
}