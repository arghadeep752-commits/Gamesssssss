package com.devdarshan.nativemodule

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.FileProvider
import java.io.File

/**
 * Shares the actual image file through a content:// URI with a temporary read grant.
 * "whatsapp" targets WhatsApp (or WhatsApp Business) directly when installed and
 * falls back to the system share sheet otherwise.
 *
 * Android does not report whether the receiving app actually sent anything, so the
 * result only says which screen was opened, never that sharing succeeded.
 */
class ShareHelper(private val context: Context) {

  fun installedWhatsApp(): String? = WHATSAPP_PACKAGES.firstOrNull { isInstalled(it) }

  /** Copies the image into the shared cache folder (on a background thread). */
  fun prepare(source: File): File {
    if (!source.exists() || source.length() == 0L) {
      throw NativeError(ErrorCodes.FILE_MISSING, "The wallpaper file is missing, please try again")
    }
    val folder = File(context.cacheDir, SHARE_DIR).apply { if (!exists()) mkdirs() }
    val staleBefore = System.currentTimeMillis() - 24 * 60 * 60 * 1000L
    folder.listFiles()?.forEach { if (it.lastModified() < staleBefore) it.delete() }
    val target = File(folder, "DevDarshan-${source.name}")
    if (!target.exists() || target.length() != source.length()) source.copyTo(target, overwrite = true)
    return target
  }

  /** Starts the share UI. Must run on the main thread. */
  fun launch(activity: Activity, shareFile: File, mimeType: String, target: String, text: String?, chooserTitle: String?): Map<String, Any?> {
    val uri = FileProvider.getUriForFile(context, authority(context), shareFile)
    val send = Intent(Intent.ACTION_SEND).apply {
      type = mimeType
      putExtra(Intent.EXTRA_STREAM, uri)
      if (!text.isNullOrBlank()) putExtra(Intent.EXTRA_TEXT, text)
      clipData = ClipData.newRawUri(shareFile.name, uri)
      addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }

    if (target == TARGET_WHATSAPP) {
      val whatsapp = installedWhatsApp()
      if (whatsapp != null) {
        try {
          activity.startActivity(Intent(send).setPackage(whatsapp))
          return mapOf(
            "opened" to true,
            "target" to if (whatsapp == WHATSAPP) "whatsapp" else "whatsappBusiness",
          )
        } catch (e: ActivityNotFoundException) {
          // Fall through to the system share sheet.
        }
      }
    }

    val chooser = Intent.createChooser(send, chooserTitle ?: "Share wallpaper").apply {
      addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    try {
      activity.startActivity(chooser)
    } catch (e: ActivityNotFoundException) {
      throw NativeError(ErrorCodes.SHARE_FAILED, "No app on this phone can share images", e)
    }
    return mapOf("opened" to true, "target" to "chooser")
  }

  @Suppress("DEPRECATION")
  private fun isInstalled(packageName: String): Boolean = try {
    if (Build.VERSION.SDK_INT >= 33) {
      context.packageManager.getPackageInfo(packageName, PackageManager.PackageInfoFlags.of(0))
    } else {
      context.packageManager.getPackageInfo(packageName, 0)
    }
    true
  } catch (e: PackageManager.NameNotFoundException) {
    false
  }

  companion object {
    const val TARGET_WHATSAPP = "whatsapp"
    private const val WHATSAPP = "com.whatsapp"
    private const val WHATSAPP_BUSINESS = "com.whatsapp.w4b"
    private val WHATSAPP_PACKAGES = listOf(WHATSAPP, WHATSAPP_BUSINESS)
    private const val SHARE_DIR = "devdarshan-share"

    fun authority(context: Context): String = "${context.packageName}.devdarshan.fileprovider"
  }
}
