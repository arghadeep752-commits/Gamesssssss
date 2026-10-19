package com.calcpro.app

import android.app.Application
import androidx.appcompat.app.AppCompatDelegate
import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactHost
import com.facebook.react.ReactNativeApplicationEntryPoint.loadReactNative
import com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost

class MainApplication : Application(), ReactApplication {

  override val reactHost: ReactHost by lazy {
    getDefaultReactHost(
      context = applicationContext,
      packageList =
        PackageList(this).packages.apply {
          // Local Turbo Native Module (storage + haptics), see CalcKitModule.
          add(CalcKitPackage())
        },
    )
  }

  override fun onCreate() {
    super.onCreate()
    applySavedTheme()
    loadReactNative(this)
  }

  /**
   * Applies the Light/Dark choice from the app's settings before the first window is drawn, so the
   * splash screen and system bars already match it.
   */
  private fun applySavedTheme() {
    val saved = getSharedPreferences(CalcKitModule.PREFS_NAME, MODE_PRIVATE).getString("theme", null)
    val mode =
      when (saved) {
        "light" -> AppCompatDelegate.MODE_NIGHT_NO
        "dark" -> AppCompatDelegate.MODE_NIGHT_YES
        else -> AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM
      }
    AppCompatDelegate.setDefaultNightMode(mode)
  }
}
