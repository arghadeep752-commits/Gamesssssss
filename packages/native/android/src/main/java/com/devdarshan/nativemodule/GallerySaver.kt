package com.devdarshan.nativemodule

import android.Manifest
import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.annotation.RequiresApi
import androidx.core.content.ContextCompat
import java.io.File
import java.io.FileInputStream
import java.io.IOException

/**
 * Saves a wallpaper to Pictures/DevDarshan so it appears in the phone's gallery.
 *
 * Android 10+ uses MediaStore (scoped storage, no permission). Android 7–9 write
 * to the public Pictures folder, which needs WRITE_EXTERNAL_STORAGE (requested by
 * the JavaScript layer only on those versions). Saving the same wallpaper twice
 * returns the existing entry instead of creating a copy.
 */
class GallerySaver(private val context: Context) {

  fun needsLegacyPermission(): Boolean =
    Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
      ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
      PackageManager.PERMISSION_GRANTED

  fun save(source: File, displayName: String, mimeType: String): Map<String, Any?> {
    if (!source.exists() || source.length() == 0L) {
      throw NativeError(ErrorCodes.FILE_MISSING, "The wallpaper file is missing, please try again")
    }
    return try {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        saveWithMediaStore(source, displayName, mimeType)
      } else {
        saveLegacy(source, displayName, mimeType)
      }
    } catch (e: NativeError) {
      throw e
    } catch (e: Exception) {
      if (e.isNoSpace()) throw NativeError(ErrorCodes.NO_SPACE, "Not enough free storage to save the wallpaper", e)
      throw NativeError(ErrorCodes.SAVE_FAILED, e.message ?: "Could not save the wallpaper", e)
    }
  }

  @RequiresApi(Build.VERSION_CODES.Q)
  private fun saveWithMediaStore(source: File, displayName: String, mimeType: String): Map<String, Any?> {
    val resolver = context.contentResolver
    val relativePath = "${Environment.DIRECTORY_PICTURES}/$FOLDER/"
    val collection = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)

    findExisting(collection, displayName, relativePath)?.let { existing ->
      return result(existing.toString(), alreadyExisted = true)
    }

    val pending = ContentValues().apply {
      put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
      put(MediaStore.Images.Media.MIME_TYPE, mimeType)
      put(MediaStore.Images.Media.RELATIVE_PATH, relativePath)
      put(MediaStore.Images.Media.IS_PENDING, 1)
    }
    val uri = resolver.insert(collection, pending)
      ?: throw NativeError(ErrorCodes.SAVE_FAILED, "The gallery did not accept the image")
    try {
      val output = resolver.openOutputStream(uri) ?: throw IOException("Could not open the gallery file")
      output.use { out -> FileInputStream(source).use { it.copyTo(out, 64 * 1024) } }
      val published = ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
      resolver.update(uri, published, null, null)
    } catch (e: Exception) {
      // Never leave a half-written, invisible entry behind.
      resolver.delete(uri, null, null)
      throw e
    }
    return result(uri.toString(), alreadyExisted = false)
  }

  @RequiresApi(Build.VERSION_CODES.Q)
  private fun findExisting(collection: Uri, displayName: String, relativePath: String): Uri? {
    val projection = arrayOf(MediaStore.Images.Media._ID, MediaStore.Images.Media.SIZE)
    val selection = "${MediaStore.Images.Media.DISPLAY_NAME} = ? AND ${MediaStore.Images.Media.RELATIVE_PATH} = ?"
    context.contentResolver.query(collection, projection, selection, arrayOf(displayName, relativePath), null)?.use { cursor ->
      if (cursor.moveToFirst()) {
        val id = cursor.getLong(0)
        val size = cursor.getLong(1)
        if (size > 0) return ContentUris.withAppendedId(collection, id)
      }
    }
    return null
  }

  @Suppress("DEPRECATION")
  private fun saveLegacy(source: File, displayName: String, mimeType: String): Map<String, Any?> {
    if (ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
      PackageManager.PERMISSION_GRANTED
    ) {
      throw NativeError(
        ErrorCodes.PERMISSION_REQUIRED,
        "Storage permission is needed to save wallpapers on this Android version",
      )
    }
    val folder = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), FOLDER)
    if (!folder.exists() && !folder.mkdirs()) {
      throw NativeError(ErrorCodes.SAVE_FAILED, "Could not create the Pictures/$FOLDER folder")
    }
    val target = File(folder, displayName)
    if (target.exists() && target.length() == source.length()) {
      return result(Uri.fromFile(target).toString(), alreadyExisted = true)
    }
    source.copyTo(target, overwrite = true)
    MediaScannerConnection.scanFile(context, arrayOf(target.absolutePath), arrayOf(mimeType), null)
    return result(Uri.fromFile(target).toString(), alreadyExisted = false)
  }

  private fun result(uri: String, alreadyExisted: Boolean): Map<String, Any?> = mapOf(
    "uri" to uri,
    "alreadyExisted" to alreadyExisted,
    "location" to "Pictures/$FOLDER",
  )

  companion object {
    const val FOLDER = "DevDarshan"
  }
}
