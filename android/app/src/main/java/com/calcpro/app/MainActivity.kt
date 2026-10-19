package com.calcpro.app

import android.content.res.Configuration
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultReactActivityDelegate

class MainActivity : ReactActivity() {

  /**
   * Returns the name of the main component registered from JavaScript. This is used to schedule
   * rendering of the component.
   */
  override fun getMainComponentName(): String = "CalcPro"

  /** Returns the instance of the [ReactActivityDelegate] (New Architecture). */
  override fun createReactActivityDelegate(): ReactActivityDelegate =
      DefaultReactActivityDelegate(this, mainComponentName)

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    applySavedWindowColor()
  }

  /**
   * Paints the window in the chosen color theme's background before React draws its first frame,
   * so starting the app or rotating the phone never flashes a different color.
   */
  private fun applySavedWindowColor() {
    val night =
        (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
            Configuration.UI_MODE_NIGHT_YES
    val prefs = getSharedPreferences(CalcKitModule.PREFS_NAME, MODE_PRIVATE)
    val hex = prefs.getString(if (night) "bg.dark" else "bg.light", null) ?: return
    try {
      window.setBackgroundDrawable(ColorDrawable(Color.parseColor(hex)))
    } catch (_: IllegalArgumentException) {
      // Keep the theme's default background.
    }
  }
}
