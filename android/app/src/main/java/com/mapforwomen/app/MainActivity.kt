package com.mapforwomen.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.mapforwomen.app.ui.AppNav
import com.mapforwomen.app.ui.theme.MapForWomenTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repository = (application as MapForWomenApp).repository
        setContent {
            MapForWomenTheme {
                AppNav(repository = repository)
            }
        }
    }
}