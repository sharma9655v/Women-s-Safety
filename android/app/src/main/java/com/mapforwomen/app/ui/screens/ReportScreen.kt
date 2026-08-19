package com.mapforwomen.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val REPORT_CATEGORIES = listOf(
    "streetlight_not_working",
    "poor_lighting",
    "harassment",
    "suspicious_activity",
    "blocked_sidewalk",
    "unsafe_transport",
    "road_hazard",
    "other",
)

/** Anonymous incident report screen.
 *
 *  Privacy contract: no identity is ever submitted; a free-text description
 *  is optional and is redacted server-side. The API confirms acceptance with
 *  a content-free response. */
@Composable
fun ReportScreen(
    repository: SafetyRepository,
    onDone: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    var category by remember { mutableStateOf("streetlight_not_working") }
    var description by remember { mutableStateOf("") }
    var segmentIdText by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var submitted by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Report an incident", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Anonymous report. No account or identity data is sent; your report is counted as evidence only after review.",
            style = MaterialTheme.typography.bodyMedium,
        )

        Text("Category: $category", style = MaterialTheme.typography.titleSmall)
        REPORT_CATEGORIES.forEach { candidate ->
            OutlinedButton(
                onClick = { category = candidate },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (category == candidate) "$candidate ✓" else candidate)
            }
        }

        TextField(
            value = segmentIdText,
            onValueChange = { segmentIdText = it.filter { char -> char.isDigit() } },
            label = { Text("Road segment id (optional)") },
            modifier = Modifier.fillMaxWidth(),
        )

        TextField(
            value = description,
            onValueChange = { description = it.take(500) },
            label = { Text("Description (optional, redacted server-side)") },
            modifier = Modifier.fillMaxWidth(),
        )

        Button(
            onClick = {
                val segmentId = segmentIdText.toIntOrNull() ?: 0
                scope.launch {
                    try {
                        val response = withContext(Dispatchers.IO) {
                            repository.report(
                                segmentId = segmentId,
                                category = category,
                                description = description.ifBlank { null },
                            )
                        }
                        submitted = true
                        message = "Report #${response.reportId} accepted (${response.verificationState})."
                    } catch (exc: Exception) {
                        message = exc.message
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Submit anonymous report")
        }

        if (submitted) {
            Button(onClick = onDone, modifier = Modifier.fillMaxWidth()) {
                Text("Done")
            }
        }

        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Spacer(Modifier.height(4.dp))
    }
}