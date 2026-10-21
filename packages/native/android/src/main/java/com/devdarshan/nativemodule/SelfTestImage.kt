package com.devdarshan.nativemodule

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Shader
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Draws a clearly labelled test image for the device self-test that test builds
 * (no Firebase project yet) offer, so CI can exercise the real wallpaper, gallery
 * and share code paths before any content exists. Every image is unique (it carries
 * a timestamp), so a successful "set wallpaper" always changes the system wallpaper.
 */
internal object SelfTestImage {
  private const val WIDTH = 1080
  private const val HEIGHT = 2340

  fun create(context: Context): Map<String, Any> {
    val bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888)
    try {
      val canvas = Canvas(bitmap)
      val paint = Paint(Paint.ANTI_ALIAS_FLAG)
      paint.shader = LinearGradient(
        0f, 0f, 0f, HEIGHT.toFloat(),
        Color.parseColor("#E07A2E"), Color.parseColor("#2E5B43"),
        Shader.TileMode.CLAMP,
      )
      canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), paint)

      paint.shader = null
      paint.color = Color.WHITE
      paint.textAlign = Paint.Align.CENTER
      paint.textSize = 96f
      paint.isFakeBoldText = true
      canvas.drawText("DevDarshan", WIDTH / 2f, HEIGHT / 2f - 60f, paint)
      paint.isFakeBoldText = false
      paint.textSize = 44f
      canvas.drawText("device self-test", WIDTH / 2f, HEIGHT / 2f + 20f, paint)
      val stamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(Date())
      canvas.drawText(stamp, WIDTH / 2f, HEIGHT / 2f + 90f, paint)

      val dir = File(context.cacheDir, "devdarshan-selftest").apply { mkdirs() }
      dir.listFiles()?.forEach { it.delete() }
      val file = File(dir, "selftest-${System.currentTimeMillis()}.png")
      FileOutputStream(file).use { out ->
        if (!bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)) {
          throw NativeError(ErrorCodes.SAVE_FAILED, "Could not encode the test image")
        }
      }
      return mapOf(
        "path" to file.absolutePath,
        "width" to WIDTH,
        "height" to HEIGHT,
        "mimeType" to "image/png",
        "bytes" to file.length().toDouble(),
      )
    } finally {
      bitmap.recycle()
    }
  }
}
