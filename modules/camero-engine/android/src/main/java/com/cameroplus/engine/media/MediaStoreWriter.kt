package com.cameroplus.engine.media

import android.content.ContentResolver
import android.content.ContentValues
import android.content.Context
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.ParcelFileDescriptor
import android.provider.MediaStore
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Writes captures and exports into shared storage through MediaStore (Android 10+) or the public
 * DCIM folder on older versions. Originals are never overwritten; every save creates a new item.
 */
object MediaStoreWriter {
  const val ALBUM = "Camero Plus"
  const val ORIGINALS = "Originals"

  enum class Kind { IMAGE, VIDEO }

  /** "dcim" keeps photos and videos together in DCIM/Camero Plus; "pictures" splits Pictures/Movies. */
  @Volatile
  var location: String = "dcim"

  private val stampFormat = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)

  fun newName(prefix: String, extension: String, suffix: String = ""): String =
    "${prefix}_${synchronized(stampFormat) { stampFormat.format(Date()) }}$suffix.$extension"

  private fun relativeDir(kind: Kind, sub: String?): String {
    val base = when {
      location == "pictures" && kind == Kind.IMAGE -> "${Environment.DIRECTORY_PICTURES}/$ALBUM"
      location == "pictures" && kind == Kind.VIDEO -> "${Environment.DIRECTORY_MOVIES}/$ALBUM"
      else -> "${Environment.DIRECTORY_DCIM}/$ALBUM"
    }
    return if (sub.isNullOrBlank()) base else "$base/$sub"
  }

  private fun legacyDir(kind: Kind, sub: String?): File {
    @Suppress("DEPRECATION")
    val root = Environment.getExternalStorageDirectory()
    return File(root, relativeDir(kind, sub)).apply { mkdirs() }
  }

  private fun collection(kind: Kind): Uri = if (Build.VERSION.SDK_INT >= 29) {
    if (kind == Kind.IMAGE) MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
    else MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
  } else {
    if (kind == Kind.IMAGE) MediaStore.Images.Media.EXTERNAL_CONTENT_URI else MediaStore.Video.Media.EXTERNAL_CONTENT_URI
  }

  /** Content values for a pending MediaStore item (Android 10+). */
  fun pendingValues(kind: Kind, displayName: String, mime: String, sub: String? = null): ContentValues =
    ContentValues().apply {
      put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
      put(MediaStore.MediaColumns.MIME_TYPE, mime)
      val now = System.currentTimeMillis()
      put(MediaStore.MediaColumns.DATE_ADDED, now / 1000)
      put(MediaStore.MediaColumns.DATE_MODIFIED, now / 1000)
      if (kind == Kind.IMAGE) put(MediaStore.Images.Media.DATE_TAKEN, now) else put(MediaStore.Video.Media.DATE_TAKEN, now)
      if (Build.VERSION.SDK_INT >= 29) {
        put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir(kind, sub))
        put(MediaStore.MediaColumns.IS_PENDING, 1)
      }
    }

  /** Copies [src] into shared storage and returns the new content URI. */
  fun saveFile(context: Context, src: File, kind: Kind, displayName: String, mime: String, sub: String? = null): Uri {
    if (Build.VERSION.SDK_INT >= 29) {
      val resolver = context.contentResolver
      val uri = resolver.insert(collection(kind), pendingValues(kind, displayName, mime, sub))
        ?: throw IllegalStateException("MediaStore refused the new item")
      try {
        resolver.openOutputStream(uri)?.use { out -> FileInputStream(src).use { it.copyTo(out, 256 * 1024) } }
          ?: throw IllegalStateException("Could not open the new item for writing")
        finishPending(resolver, uri)
        return uri
      } catch (e: Exception) {
        resolver.delete(uri, null, null)
        throw e
      }
    }
    val target = File(legacyDir(kind, sub), displayName)
    src.inputStream().use { input -> FileOutputStream(target).use { input.copyTo(it, 256 * 1024) } }
    return scan(context, target, mime)
  }

  /**
   * Opens a new, empty item for writing (used by MediaMuxer for time-lapse). Call [finishPending]
   * after closing the descriptor, or [delete] on failure.
   */
  fun openForWrite(context: Context, kind: Kind, displayName: String, mime: String): Pair<Uri, ParcelFileDescriptor> {
    if (Build.VERSION.SDK_INT >= 29) {
      val resolver = context.contentResolver
      val uri = resolver.insert(collection(kind), pendingValues(kind, displayName, mime))
        ?: throw IllegalStateException("MediaStore refused the new item")
      val pfd = resolver.openFileDescriptor(uri, "rw") ?: throw IllegalStateException("Could not open the new item")
      return uri to pfd
    }
    val target = File(legacyDir(kind, null), displayName)
    val pfd = ParcelFileDescriptor.open(
      target,
      ParcelFileDescriptor.MODE_CREATE or ParcelFileDescriptor.MODE_READ_WRITE or ParcelFileDescriptor.MODE_TRUNCATE
    )
    return Uri.fromFile(target) to pfd
  }

  /** Publishes a pending item. For legacy file URIs this triggers a media scan and returns its content URI. */
  fun publish(context: Context, uri: Uri, mime: String): Uri {
    if (uri.scheme == ContentResolver.SCHEME_FILE) {
      val path = uri.path ?: return uri
      return scan(context, File(path), mime)
    }
    finishPending(context.contentResolver, uri)
    return uri
  }

  fun finishPending(resolver: ContentResolver, uri: Uri) {
    if (Build.VERSION.SDK_INT >= 29) {
      val values = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
      resolver.update(uri, values, null, null)
    }
  }

  fun delete(context: Context, uri: Uri) {
    try {
      if (uri.scheme == ContentResolver.SCHEME_FILE) {
        uri.path?.let { File(it).delete() }
      } else {
        context.contentResolver.delete(uri, null, null)
      }
    } catch (_: Exception) {
    }
  }

  /** Values for CameraX MediaStoreOutputOptions (video recording). */
  fun videoContentValues(displayName: String): ContentValues = ContentValues().apply {
    put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
    put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
    if (Build.VERSION.SDK_INT >= 29) put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir(Kind.VIDEO, null))
  }

  fun videoCollection(): Uri = collection(Kind.VIDEO)

  fun imageCollection(): Uri = collection(Kind.IMAGE)

  /** Values for CameraX ImageCapture output straight into MediaStore (RAW/DNG, Ultra HDR). */
  fun imageContentValues(displayName: String, mime: String, sub: String? = null): ContentValues = ContentValues().apply {
    put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
    put(MediaStore.MediaColumns.MIME_TYPE, mime)
    if (Build.VERSION.SDK_INT >= 29) put(MediaStore.MediaColumns.RELATIVE_PATH, relativeDir(Kind.IMAGE, sub))
  }

  fun legacyVideoFile(displayName: String): File = File(legacyDir(Kind.VIDEO, null), displayName)

  fun legacyImageFile(displayName: String, sub: String? = null): File = File(legacyDir(Kind.IMAGE, sub), displayName)

  fun scan(context: Context, file: File, mime: String): Uri {
    val latch = CountDownLatch(1)
    var result: Uri? = null
    MediaScannerConnection.scanFile(context, arrayOf(file.absolutePath), arrayOf(mime)) { _, uri ->
      result = uri
      latch.countDown()
    }
    latch.await(4, TimeUnit.SECONDS)
    return result ?: Uri.fromFile(file)
  }
}
