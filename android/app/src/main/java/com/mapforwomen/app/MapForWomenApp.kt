package com.mapforwomen.app

import android.app.Application
import com.mapforwomen.app.data.AuthManager
import com.mapforwomen.app.data.SafetyRepository
import org.osmdroid.config.Configuration

class MapForWomenApp : Application() {

    val authManager: AuthManager by lazy { AuthManager(this) }
    val repository: SafetyRepository by lazy { SafetyRepository(authManager) }

    override fun onCreate() {
        super.onCreate()
        Configuration.getInstance().apply {
            userAgentValue = packageName
            load(context = this@MapForWomenApp, prefs = getSharedPreferences("osmdroid", MODE_PRIVATE))
        }
    }
}