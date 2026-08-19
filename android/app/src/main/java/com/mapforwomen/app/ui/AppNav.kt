package com.mapforwomen.app.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Science
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Sos
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.mapforwomen.app.data.SafetyRepository
import com.mapforwomen.app.ui.screens.EmergencyScreen
import com.mapforwomen.app.ui.screens.GuardianScreen
import com.mapforwomen.app.ui.screens.HomeScreen
import com.mapforwomen.app.ui.screens.ModelsScreen
import com.mapforwomen.app.ui.screens.ReportScreen
import com.mapforwomen.app.ui.screens.RouteScreen

private data class Tab(
    val route: String,
    val label: String,
    val icon: ImageVector,
)

private val tabs = listOf(
    Tab("home", "Map", Icons.Filled.Home),
    Tab("route", "Route", Icons.Filled.VerifiedUser),
    Tab("emergency", "SOS", Icons.Filled.Sos),
    Tab("guardian", "Guardian", Icons.Filled.Shield),
    Tab("models", "Models", Icons.Filled.Science),
)

@Composable
fun AppNav(repository: SafetyRepository) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination
    val context = LocalContext.current

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    val selected = currentDestination?.hierarchy
                        ?.any { it.route == tab.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = androidx.compose.ui.Modifier.padding(padding),
        ) {
            composable("home") {
                HomeScreen(
                    repository,
                    onOpenRoute = { navController.navigate("route") },
                    onOpenReport = { navController.navigate("report") },
                )
            }
            composable("route") { RouteScreen(repository) }
            composable("emergency") { EmergencyScreen(repository, context) }
            composable("guardian") { GuardianScreen(repository, context) }
            composable("models") { ModelsScreen(repository) }
            composable("report") { ReportScreen(repository, onDone = { navController.popBackStack() }) }
        }
    }
}