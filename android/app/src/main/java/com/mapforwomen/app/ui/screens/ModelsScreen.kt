package com.mapforwomen.app.ui.screens

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
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.mapforwomen.app.data.SafetyRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Model status screen — intentionally honest.
 *
 *  Shows the ML gate (closed until >=1000 VERIFIED observations over >=90
 *  days) and the CV checkpoint registry with statuses. When the server runs
 *  the development CV mock, that is stated explicitly (is_real_inference is
 *  reported by the API); nothing here claims a real model is deployed. */
@Composable
fun ModelsScreen(repository: SafetyRepository) {
    val scope = rememberCoroutineScope()
    var riskModel by remember { mutableStateOf<String?>(null) }
    var evidenceModel by remember { mutableStateOf<String?>(null) }
    var gateOpen by remember { mutableStateOf(false) }
    var verified by remember { mutableStateOf(0) }
    var minVerified by remember { mutableStateOf(1000) }
    var spanDays by remember { mutableStateOf<Double?>(null) }
    var minSpanDays by remember { mutableStateOf(90) }
    var cvModels by remember { mutableStateOf<List<com.mapforwomen.app.data.remote.CvModelInfoDto>>(emptyList()) }
    var message by remember { mutableStateOf<String?>(null) }

    fun load() {
        scope.launch {
            try {
                val status = withContext(Dispatchers.IO) { repository.models() }
                riskModel = status.riskModel
                evidenceModel = status.evidenceModel
                gateOpen = status.mlGate.open
                verified = status.mlGate.verifiedObservations
                minVerified = status.mlGate.minVerifiedObservations
                spanDays = status.mlGate.spanDays
                minSpanDays = status.mlGate.minSpanDays
                cvModels = status.cvModels
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
        Text("Model status", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Status is reported from the live API; it never claims a model is validated when it is not.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Button(onClick = { load() }, modifier = Modifier.fillMaxWidth()) {
            Text("Refresh status")
        }

        riskModel?.let {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("Active risk model: $it", style = MaterialTheme.typography.titleSmall)
                    Text("evidence model: ${evidenceModel ?: "unknown"}")
                    Text(
                        if (gateOpen) {
                            "ML training gate: OPEN"
                        } else {
                            "ML training gate: CLOSED — $verified / $minVerified verified observations" +
                                (spanDays?.let { " over ${"%.1f".format(it)} / $minSpanDays days" } ?: "")
                        },
                        color = if (gateOpen) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.error,
                    )
                }
            }
        }

        cvModels.forEach { model ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("${model.name} v${model.version} (${model.kind})", style = MaterialTheme.typography.titleSmall)
                    Text("framework: ${model.framework} · status: ${model.status}")
                    Text("integration: ${model.integration}")
                    if (model.status != "PRODUCTION") {
                        Text(
                            "Not validated for production use.",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }

        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Spacer(Modifier.height(4.dp))
    }
}