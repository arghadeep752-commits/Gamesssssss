package com.devdarshan.nativemodule

import android.content.Context
import android.graphics.BitmapFactory
import android.os.StatFs
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean

data class CachedImage(
  val file: File,
  val mimeType: String,
  val width: Int,
  val height: Int,
  val fromCache: Boolean,
) {
  fun toMap(): Map<String, Any?> = mapOf(
    "path" to file.absolutePath,
    "uri" to "file://${file.absolutePath}",
    "mimeType" to mimeType,
    "bytes" to file.length().toDouble(),
    "width" to width,
    "height" to height,
    "fromCache" to fromCache,
  )
}

/**
 * Downloads full-resolution originals into the app cache so "Set wallpaper",
 * "Download" and "Share" reuse one copy. Writes go to a ".part" file that is only
 * renamed after the image decodes, so a broken download is never treated as valid.
 * The cache is trimmed to stay below [MAX_BYTES].
 */
class ImageCache(private val context: Context) {
  private val cancelFlags = ConcurrentHashMap<String, AtomicBoolean>()
  private val keyLocks = ConcurrentHashMap<String, Any>()

  private val directory: File
    get() = File(context.cacheDir, DIR_NAME).apply { if (!exists()) mkdirs() }

  fun cancel(key: String) {
    cancelFlags[safeKey(key)]?.set(true)
  }

  fun find(key: String): CachedImage? {
    val safe = safeKey(key)
    val file = directory.listFiles()?.firstOrNull {
      it.isFile && it.name.startsWith("$safe.") && !it.name.endsWith(PART_SUFFIX) && it.length() > 0
    } ?: return null
    val bounds = decodeBounds(file)
    if (bounds == null) {
      file.delete()
      return null
    }
    file.setLastModified(System.currentTimeMillis())
    return CachedImage(file, mimeForExtension(file.extension), bounds.first, bounds.second, true)
  }

  fun download(key: String, url: String, onProgress: (Long, Long) -> Unit): CachedImage {
    val safe = safeKey(key)
    val lock = keyLocks.getOrPut(safe) { Any() }
    synchronized(lock) {
      // A concurrent request for the same image waits here and then reuses the finished file.
      find(key)?.let { return it }

      val cancelled = AtomicBoolean(false)
      cancelFlags[safe] = cancelled
      val part = File(directory, "$safe$PART_SUFFIX")
      var connection: HttpURLConnection? = null
      try {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
          connectTimeout = 15_000
          readTimeout = 30_000
          instanceFollowRedirects = true
          setRequestProperty("Accept", "image/*")
        }
        connection = conn
        val status = conn.responseCode
        if (status !in 200..299) {
          throw NativeError(ErrorCodes.HTTP, "The image server answered with HTTP $status")
        }
        val total = conn.contentLengthLong
        ensureSpace(total)
        val contentType = (conn.contentType ?: "").substringBefore(';').trim().lowercase()

        var written = 0L
        var lastEmit = 0L
        conn.inputStream.use { input ->
          FileOutputStream(part).use { output ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
              if (cancelled.get()) throw NativeError(ErrorCodes.CANCELLED, "Download cancelled")
              val read = input.read(buffer)
              if (read == -1) break
              output.write(buffer, 0, read)
              written += read
              val now = System.currentTimeMillis()
              if (now - lastEmit >= PROGRESS_INTERVAL_MS) {
                lastEmit = now
                onProgress(written, total)
              }
            }
            output.fd.sync()
          }
        }
        if (total > 0 && written != total) {
          throw NativeError(ErrorCodes.NETWORK, "The download was interrupted, please try again")
        }
        onProgress(written, if (total > 0) total else written)

        val bounds = decodeBounds(part)
          ?: throw NativeError(ErrorCodes.INVALID_IMAGE, "The downloaded file is not a valid image")
        val extension = extensionFor(contentType, part)
        val target = File(directory, "$safe.$extension")
        if (target.exists()) target.delete()
        if (!part.renameTo(target)) {
          throw NativeError(ErrorCodes.SAVE_FAILED, "Could not store the downloaded image")
        }
        trim(keep = target)
        return CachedImage(target, mimeForExtension(extension), bounds.first, bounds.second, false)
      } catch (e: NativeError) {
        part.delete()
        throw e
      } catch (e: UnknownHostException) {
        part.delete()
        throw NativeError(ErrorCodes.NETWORK, "No internet connection", e)
      } catch (e: SocketTimeoutException) {
        part.delete()
        throw NativeError(ErrorCodes.NETWORK, "The connection timed out", e)
      } catch (e: IOException) {
        part.delete()
        if (e.isNoSpace()) throw NativeError(ErrorCodes.NO_SPACE, "Not enough free storage", e)
        throw NativeError(ErrorCodes.NETWORK, e.message ?: "Network error", e)
      } finally {
        connection?.disconnect()
        cancelFlags.remove(safe)
      }
    }
  }

  fun size(): Long = directory.listFiles()?.sumOf { it.length() } ?: 0L

  fun clear(): Long {
    var freed = 0L
    directory.listFiles()?.forEach { file ->
      val length = file.length()
      if (file.delete()) freed += length
    }
    return freed
  }

  private fun ensureSpace(expectedBytes: Long) {
    val available = try {
      StatFs(directory.path).availableBytes
    } catch (e: IllegalArgumentException) {
      Long.MAX_VALUE
    }
    val needed = if (expectedBytes > 0) expectedBytes + SPACE_MARGIN else MIN_FREE_UNKNOWN_SIZE
    if (available < needed) throw NativeError(ErrorCodes.NO_SPACE, "Not enough free storage")
  }

  /** Keeps the cache small: removes stale partial files and the least recently used images. */
  private fun trim(keep: File) {
    val files = directory.listFiles()?.toMutableList() ?: return
    val staleBefore = System.currentTimeMillis() - 60 * 60 * 1000L
    files.filter { it.name.endsWith(PART_SUFFIX) && it.lastModified() < staleBefore }.forEach { it.delete() }
    var total = files.filter { it.exists() }.sumOf { it.length() }
    if (total <= MAX_BYTES) return
    files.filter { it.exists() && it != keep }.sortedBy { it.lastModified() }.forEach { file ->
      if (total <= TARGET_BYTES) return
      val length = file.length()
      if (file.delete()) total -= length
    }
  }

  companion object {
    private const val DIR_NAME = "devdarshan-originals"
    private const val PART_SUFFIX = ".part"
    private const val PROGRESS_INTERVAL_MS = 120L
    private const val SPACE_MARGIN = 20L * 1024 * 1024
    private const val MIN_FREE_UNKNOWN_SIZE = 50L * 1024 * 1024
    private const val MAX_BYTES = 150L * 1024 * 1024
    private const val TARGET_BYTES = 100L * 1024 * 1024

    fun safeKey(key: String): String = key.replace(Regex("[^A-Za-z0-9_-]"), "_").take(80).ifEmpty { "image" }

    fun decodeBounds(file: File): Pair<Int, Int>? {
      val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
      BitmapFactory.decodeFile(file.absolutePath, options)
      return if (options.outWidth > 0 && options.outHeight > 0) options.outWidth to options.outHeight else null
    }

    fun mimeForExtension(extension: String): String = when (extension.lowercase()) {
      "png" -> "image/png"
      "webp" -> "image/webp"
      else -> "image/jpeg"
    }

    private fun extensionFor(contentType: String, file: File): String {
      when (contentType) {
        "image/png" -> return "png"
        "image/webp" -> return "webp"
        "image/jpeg", "image/jpg" -> return "jpg"
      }
      val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
      BitmapFactory.decodeFile(file.absolutePath, options)
      return when (options.outMimeType) {
        "image/png" -> "png"
        "image/webp" -> "webp"
        else -> "jpg"
      }
    }
  }
}
