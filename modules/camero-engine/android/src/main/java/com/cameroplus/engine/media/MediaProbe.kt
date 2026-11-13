package com.cameroplus.engine.media

import android.content.ContentResolver
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.provider.OpenableColumns
import android.util.Size
import androidx.exifinterface.media.ExifInterface
import java.io.File
import java.io.FileOutputStream
import kotlin.math.max
import kotlin.math.roundToInt

/** Reads facts about media files: sizes, codecs, EXIF, thumbnails and timeline frames. */
object MediaProbe {
  fun parse(uri: String): Uri = if (uri.startsWith("/")) Uri.fromFile(File(uri)) else Uri.parse(uri)

  private fun cacheDir(context: Context, name: String): File = File(context.cacheDir, name).apply { mkdirs() }

  fun isVideo(context: Context, uri: Uri): Boolean {
    val type = mimeType(context, uri) ?: return false
    return type.startsWith("video/")
  }

  fun mimeType(context: Context, uri: Uri): String? {
    if (uri.scheme == ContentResolver.SCHEME_CONTENT) context.contentResolver.getType(uri)?.let { return it }
    val path = (uri.path ?: uri.toString()).lowercase()
    return when {
      path.endsWith(".jpg") || path.endsWith(".jpeg") -> "image/jpeg"
      path.endsWith(".png") -> "image/png"
      path.endsWith(".heic") || path.endsWith(".heif") -> "image/heic"
      path.endsWith(".dng") -> "image/x-adobe-dng"
      path.endsWith(".webp") -> "image/webp"
      path.endsWith(".mp4") || path.endsWith(".m4v") -> "video/mp4"
      path.endsWith(".3gp") -> "video/3gpp"
      path.endsWith(".mkv") -> "video/x-matroska"
      path.endsWith(".webm") -> "video/webm"
      else -> null
    }
  }

  fun fileSize(context: Context, uri: Uri): Long {
    if (uri.scheme == ContentResolver.SCHEME_FILE) return File(uri.path ?: return -1).length()
    return try {
      context.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { c ->
        if (c.moveToFirst() && !c.isNull(0)) c.getLong(0) else -1L
      } ?: -1L
    } catch (e: Exception) {
      -1L
    }
  }

  fun exifOrientation(context: Context, uri: Uri): Int = try {
    context.contentResolver.openInputStream(uri)?.use { ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, 1) } ?: 1
  } catch (e: Exception) {
    1
  }

  /** Stored pixel size of an image (before EXIF orientation). */
  fun storedImageSize(context: Context, uri: Uri): IntArray {
    val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }
    return intArrayOf(opts.outWidth, opts.outHeight)
  }

  /** Decodes an image no larger than [maxEdge] on its long side, keeping stored orientation. */
  fun decodeSampled(context: Context, uri: Uri, maxEdge: Int): Bitmap? {
    val size = storedImageSize(context, uri)
    if (size[0] <= 0 || size[1] <= 0) return null
    var sample = 1
    while (max(size[0], size[1]) / (sample * 2) >= maxEdge) sample *= 2
    val opts = BitmapFactory.Options().apply {
      inSampleSize = sample
      inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    val decoded = context.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null
    val longEdge = max(decoded.width, decoded.height)
    if (longEdge <= maxEdge) return decoded
    val scale = maxEdge.toFloat() / longEdge
    val scaled = Bitmap.createScaledBitmap(decoded, max(1, (decoded.width * scale).roundToInt()), max(1, (decoded.height * scale).roundToInt()), true)
    if (scaled != decoded) decoded.recycle()
    return scaled
  }

  private fun orientBitmap(bitmap: Bitmap, orientation: Int): Bitmap {
    val m = Matrix()
    when (orientation) {
      2 -> m.setScale(-1f, 1f)
      3 -> m.setRotate(180f)
      4 -> m.setScale(1f, -1f)
      5 -> { m.setRotate(90f); m.postScale(-1f, 1f) }
      6 -> m.setRotate(90f)
      7 -> { m.setRotate(-90f); m.postScale(-1f, 1f) }
      8 -> m.setRotate(-90f)
      else -> return bitmap
    }
    val out = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
    if (out != bitmap) bitmap.recycle()
    return out
  }

  /** Small JPEG thumbnail in the cache. Returns a file:// URI string. */
  fun thumbnail(context: Context, uriString: String, maxSize: Int): String? {
    val uri = parse(uriString)
    val key = "${uriString.hashCode()}_${maxSize}"
    val file = File(cacheDir(context, "thumbs"), "$key.jpg")
    if (file.exists() && file.length() > 0) return Uri.fromFile(file).toString()
    val bitmap: Bitmap = try {
      if (isVideo(context, uri)) {
        videoFrame(context, uri, 0L, maxSize) ?: return null
      } else if (Build.VERSION.SDK_INT >= 29 && uri.scheme == ContentResolver.SCHEME_CONTENT) {
        context.contentResolver.loadThumbnail(uri, Size(maxSize, maxSize), null)
      } else {
        val raw = decodeSampled(context, uri, maxSize) ?: return null
        orientBitmap(raw, exifOrientation(context, uri))
      }
    } catch (e: Exception) {
      return null
    }
    FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.JPEG, 86, it) }
    bitmap.recycle()
    return Uri.fromFile(file).toString()
  }

  fun videoFrame(context: Context, uri: Uri, timeUs: Long, maxEdge: Int): Bitmap? {
    val r = MediaMetadataRetriever()
    return try {
      r.setDataSource(context, uri)
      val w = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
      val h = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
      val rot = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)?.toIntOrNull() ?: 0
      val dw = if (rot == 90 || rot == 270) h else w
      val dh = if (rot == 90 || rot == 270) w else h
      if (Build.VERSION.SDK_INT >= 27 && dw > 0 && dh > 0) {
        val scale = minOf(1f, maxEdge.toFloat() / max(dw, dh))
        r.getScaledFrameAtTime(timeUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, max(1, (dw * scale).roundToInt()), max(1, (dh * scale).roundToInt()))
      } else {
        val frame = r.getFrameAtTime(timeUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC) ?: return null
        val long = max(frame.width, frame.height)
        if (long <= maxEdge) frame else {
          val s = maxEdge.toFloat() / long
          Bitmap.createScaledBitmap(frame, max(1, (frame.width * s).roundToInt()), max(1, (frame.height * s).roundToInt()), true)
        }
      }
    } catch (e: Exception) {
      null
    } finally {
      try { r.release() } catch (_: Exception) {}
    }
  }

  /** Evenly spaced frames for the trim timeline. */
  fun frames(context: Context, uriString: String, count: Int, height: Int): List<String> {
    val uri = parse(uriString)
    val r = MediaMetadataRetriever()
    val out = ArrayList<String>()
    try {
      r.setDataSource(context, uri)
      val durationMs = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
      val w = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 16
      val h = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 9
      val rot = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)?.toIntOrNull() ?: 0
      val aspect = if (rot == 90 || rot == 270) h.toFloat() / w else w.toFloat() / h
      val fh = height
      val fw = max(1, (height * aspect).roundToInt())
      val dir = cacheDir(context, "frames")
      for (i in 0 until count) {
        val t = if (count <= 1) 0L else durationMs * 1000L * i / (count - 1)
        val file = File(dir, "${uriString.hashCode()}_${height}_$i.jpg")
        if (!file.exists()) {
          val frame = if (Build.VERSION.SDK_INT >= 27) {
            r.getScaledFrameAtTime(t, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, fw, fh)
          } else {
            r.getFrameAtTime(t, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)?.let { Bitmap.createScaledBitmap(it, fw, fh, true) }
          } ?: continue
          FileOutputStream(file).use { frame.compress(Bitmap.CompressFormat.JPEG, 80, it) }
          frame.recycle()
        }
        out.add(Uri.fromFile(file).toString())
      }
    } catch (_: Exception) {
    } finally {
      try { r.release() } catch (_: Exception) {}
    }
    return out
  }

  fun probe(context: Context, uriString: String): Map<String, Any?> {
    val uri = parse(uriString)
    val info = HashMap<String, Any?>()
    val mime = mimeType(context, uri)
    info["mime"] = mime
    info["bytes"] = fileSize(context, uri)
    if (mime?.startsWith("video/") == true) {
      probeVideo(context, uri, info)
    } else {
      probeImage(context, uri, info)
    }
    return info
  }

  private fun probeImage(context: Context, uri: Uri, info: HashMap<String, Any?>) {
    val size = storedImageSize(context, uri)
    var orientation = 1
    try {
      context.contentResolver.openInputStream(uri)?.use { stream ->
        val exif = ExifInterface(stream)
        orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, 1)
        info["make"] = exif.getAttribute(ExifInterface.TAG_MAKE)
        info["model"] = exif.getAttribute(ExifInterface.TAG_MODEL)
        info["dateTime"] = exif.getAttribute(ExifInterface.TAG_DATETIME_ORIGINAL) ?: exif.getAttribute(ExifInterface.TAG_DATETIME)
        info["iso"] = exif.getAttributeInt(ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY, 0).takeIf { it > 0 }
        info["exposureTime"] = exif.getAttributeDouble(ExifInterface.TAG_EXPOSURE_TIME, 0.0).takeIf { it > 0 }
        info["fNumber"] = exif.getAttributeDouble(ExifInterface.TAG_F_NUMBER, 0.0).takeIf { it > 0 }
        info["focalLength"] = exif.getAttributeDouble(ExifInterface.TAG_FOCAL_LENGTH, 0.0).takeIf { it > 0 }
        info["focalLength35"] = exif.getAttributeInt(ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM, 0).takeIf { it > 0 }
        info["software"] = exif.getAttribute(ExifInterface.TAG_SOFTWARE)
        info["flash"] = exif.getAttributeInt(ExifInterface.TAG_FLASH, 0) and 1 == 1
      }
    } catch (_: Exception) {
    }
    val swap = orientation in 5..8
    info["width"] = if (swap) size[1] else size[0]
    info["height"] = if (swap) size[0] else size[1]
    info["orientation"] = orientation
    info["kind"] = "photo"
  }

  private fun probeVideo(context: Context, uri: Uri, info: HashMap<String, Any?>) {
    info["kind"] = "video"
    val r = MediaMetadataRetriever()
    try {
      r.setDataSource(context, uri)
      val w = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
      val h = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
      val rot = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)?.toIntOrNull() ?: 0
      info["width"] = if (rot == 90 || rot == 270) h else w
      info["height"] = if (rot == 90 || rot == 270) w else h
      info["rotation"] = rot
      info["durationMs"] = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull()
      info["bitrate"] = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_BITRATE)?.toLongOrNull()
      info["hasAudio"] = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_AUDIO) == "yes"
      info["captureFps"] = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE)?.toFloatOrNull()
      info["dateTime"] = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DATE)
    } catch (_: Exception) {
    } finally {
      try { r.release() } catch (_: Exception) {}
    }
    val extractor = MediaExtractor()
    try {
      extractor.setDataSource(context, uri, null)
      for (i in 0 until extractor.trackCount) {
        val f = extractor.getTrackFormat(i)
        val m = f.getString(MediaFormat.KEY_MIME) ?: continue
        if (m.startsWith("video/")) {
          info["videoCodec"] = m
          if (f.containsKey(MediaFormat.KEY_FRAME_RATE)) {
            info["fps"] = try { f.getInteger(MediaFormat.KEY_FRAME_RATE).toFloat() } catch (e: Exception) { f.getFloat(MediaFormat.KEY_FRAME_RATE) }
          }
          if (Build.VERSION.SDK_INT >= 24 && f.containsKey(MediaFormat.KEY_COLOR_TRANSFER)) {
            val transfer = f.getInteger(MediaFormat.KEY_COLOR_TRANSFER)
            info["hdr"] = transfer == MediaFormat.COLOR_TRANSFER_HLG || transfer == MediaFormat.COLOR_TRANSFER_ST2084
          }
        } else if (m.startsWith("audio/")) {
          info["audioCodec"] = m
        }
      }
    } catch (_: Exception) {
    } finally {
      extractor.release()
    }
  }

  fun storage(): Map<String, Any> {
    @Suppress("DEPRECATION")
    val stat = StatFs(Environment.getExternalStorageDirectory().path)
    return mapOf("freeBytes" to stat.availableBytes, "totalBytes" to stat.totalBytes)
  }

  fun clearCache(context: Context) {
    for (name in listOf("thumbs", "frames", "looks", "capture", "export")) {
      File(context.cacheDir, name).listFiles()?.forEach { it.delete() }
    }
  }
}
