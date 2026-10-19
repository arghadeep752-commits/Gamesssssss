package com.calcpro.app

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.view.HapticFeedbackConstants
import com.calcpro.app.specs.NativeCalcKitSpec
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.UiThreadUtil

/**
 * Turbo Native Module behind src/specs/NativeCalcKit.ts.
 *
 * Stores settings, the calculation tape and the current input in
 * SharedPreferences (synchronous reads keep the first frame complete), and
 * plays the system keyboard haptic on key presses.
 */
class CalcKitModule(reactContext: ReactApplicationContext) : NativeCalcKitSpec(reactContext) {

  private val prefs: SharedPreferences =
      reactContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

  override fun getName(): String = NAME

  override fun getItem(key: String): String? = prefs.getString(key, null)

  override fun setItem(key: String, value: String) {
    prefs.edit().putString(key, value).apply()
  }

  override fun removeItem(key: String) {
    prefs.edit().remove(key).apply()
  }

  override fun haptic(kind: String) {
    val activity = reactApplicationContext.currentActivity ?: return
    val feedback =
        when (kind) {
          "confirm" ->
              if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) HapticFeedbackConstants.CONFIRM
              else HapticFeedbackConstants.VIRTUAL_KEY
          "long" -> HapticFeedbackConstants.LONG_PRESS
          else -> HapticFeedbackConstants.KEYBOARD_TAP
        }
    UiThreadUtil.runOnUiThread { activity.window?.decorView?.performHapticFeedback(feedback) }
  }

  companion object {
    const val NAME = "CalcKit"
    const val PREFS_NAME = "calcpro"
  }
}
