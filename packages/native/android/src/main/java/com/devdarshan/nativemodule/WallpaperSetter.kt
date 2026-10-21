package com.devdarshan.nativemodule

import android.app.WallpaperManager
import android.content.Context
import android.os.Build
import java.io.File
import java.io.FileInputStream

/**
 * Sets the home and/or lock screen wallpaper with WallpaperManager.
 *
 * "Both" is applied as two separate operations (FLAG_SYSTEM, then FLAG_LOCK), so a
 * device that refuses one destination still gets the other, and the result reports
 * each destination honestly instead of claiming success for both.
 */
class WallpaperSetter(private val context: Context) {

  fun capabilities(): Map<String, Any?> {
    val manager = WallpaperManager.getInstance(context)
    return mapOf(
      "wallpaperSupported" to manager.isWallpaperSupported,
      "setWallpaperAllowed" to manager.isSetWallpaperAllowed,
      // FLAG_LOCK exists on every Android version this app supports (7.0+).
      "lockScreenSupported" to true,
      "lockFollowsHome" to lockFollowsHome(manager),
      "sdkInt" to Build.VERSION.SDK_INT,
      "manufacturer" to Build.MANUFACTURER,
      "brand" to Build.BRAND,
      "model" to Build.MODEL,
    )
  }

  fun set(file: File, target: String): Map<String, Any?> {
    if (!file.exists() || file.length() == 0L) {
      throw NativeError(ErrorCodes.FILE_MISSING, "The wallpaper file is missing, please try again")
    }
    val manager = WallpaperManager.getInstance(context)
    if (!manager.isWallpaperSupported) {
      throw NativeError(ErrorCodes.WALLPAPER_UNSUPPORTED, "This device does not support wallpapers")
    }
    if (!manager.isSetWallpaperAllowed) {
      throw NativeError(
        ErrorCodes.WALLPAPER_NOT_ALLOWED,
        "Changing the wallpaper is blocked on this device, for example by a work or school policy",
      )
    }

    val wantHome = target == TARGET_HOME || target == TARGET_BOTH
    val wantLock = target == TARGET_LOCK || target == TARGET_BOTH
    if (!wantHome && !wantLock) throw IllegalArgumentException("Unknown wallpaper target: $target")

    val lockFollowedHome = lockFollowsHome(manager)
    var home = RESULT_SKIPPED
    var lock = RESULT_SKIPPED
    var homeError: String? = null
    var lockError: String? = null

    if (wantHome) {
      try {
        home = if (apply(manager, file, WallpaperManager.FLAG_SYSTEM)) RESULT_SET else RESULT_FAILED
        if (home == RESULT_FAILED) homeError = "The system did not accept the image"
      } catch (e: Exception) {
        home = RESULT_FAILED
        homeError = e.message ?: e.javaClass.simpleName
      }
    }
    if (wantLock) {
      try {
        lock = if (apply(manager, file, WallpaperManager.FLAG_LOCK)) RESULT_SET else RESULT_FAILED
        if (lock == RESULT_FAILED) lockError = "The system did not accept the image for the lock screen"
      } catch (e: Exception) {
        lock = RESULT_FAILED
        lockError = e.message ?: e.javaClass.simpleName
      }
    }

    if (home != RESULT_SET && lock != RESULT_SET) {
      throw NativeError(ErrorCodes.WALLPAPER_FAILED, homeError ?: lockError ?: "The system rejected the wallpaper")
    }

    return mapOf(
      "home" to home,
      "lock" to lock,
      "homeError" to homeError,
      "lockError" to lockError,
      // When the lock screen was mirroring the home screen, Android shows a new
      // home-only wallpaper on the lock screen too. Reported so the app can say so.
      "lockMirrorsHome" to (target == TARGET_HOME && lockFollowedHome == true),
      "manufacturer" to Build.MANUFACTURER,
    )
  }

  /** Streams the file to WallpaperManager; the system decodes and scales it for the display. */
  private fun apply(manager: WallpaperManager, file: File, which: Int): Boolean =
    FileInputStream(file).use { input -> manager.setStream(input, null, true, which) != 0 }

  private fun lockFollowsHome(manager: WallpaperManager): Boolean? = try {
    manager.getWallpaperId(WallpaperManager.FLAG_LOCK) < 0
  } catch (e: Exception) {
    null
  }

  companion object {
    const val TARGET_HOME = "home"
    const val TARGET_LOCK = "lock"
    const val TARGET_BOTH = "both"
    private const val RESULT_SET = "set"
    private const val RESULT_FAILED = "failed"
    private const val RESULT_SKIPPED = "skipped"
  }
}
