package com.cameroplus.engine

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.camera.extensions.ExtensionsManager
import androidx.camera.lifecycle.ProcessCameraProvider
import com.cameroplus.engine.camera.CameraCatalog
import com.cameroplus.engine.edit.PhotoRenderer
import com.cameroplus.engine.edit.VideoExportOptions
import com.cameroplus.engine.edit.VideoExporter
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.looks.LookLibrary
import com.cameroplus.engine.looks.LutCache
import com.cameroplus.engine.media.MediaProbe
import com.cameroplus.engine.media.MediaStoreWriter
import expo.modules.kotlin.Promise
import expo.modules.kotlin.functions.Queues
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.util.concurrent.TimeUnit

/** Capabilities, looks, export and media helpers. Camera control lives in CameroCameraModule. */
@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
class CameroEngineModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw IllegalStateException("App context unavailable")

  private var exporter: VideoExporter? = null
  private var cachedCapabilities: Map<String, Any?>? = null

  override fun definition() = ModuleDefinition {
    Name("CameroEngine")
    Events("onExportProgress")

    AsyncFunction("getCapabilities") { refresh: Boolean ->
      cachedCapabilities?.let { if (!refresh) return@AsyncFunction it }
      val ctx = context
      val provider = ProcessCameraProvider.getInstance(ctx).get(10, TimeUnit.SECONDS)
      val extensions = try {
        ExtensionsManager.getInstanceAsync(ctx, provider).get(6, TimeUnit.SECONDS)
      } catch (e: Exception) {
        null
      }
      val caps = CameraCatalog.describe(ctx, provider, extensions)
      cachedCapabilities = caps
      caps
    }

    AsyncFunction("getLooks") {
      LookLibrary.looks.map { spec ->
        mapOf(
          "id" to spec.id,
          "name" to spec.name,
          "collection" to spec.collection,
          "swatch" to LutCache.toneSignature(spec)
        )
      }
    }

    AsyncFunction("renderLookPreviews") { uri: String, size: Int, ids: List<String> ->
      PhotoRenderer.renderLookPreviews(context, MediaProbe.parse(uri), size.coerceIn(64, 512), ids)
    }

    AsyncFunction("exportPhoto") { uri: String, gradeJson: String?, transformJson: String?, format: String, quality: Int ->
      val ctx = context
      val ext = if (format == "png") "png" else "jpg"
      val mime = if (format == "png") "image/png" else "image/jpeg"
      val temp = File(File(ctx.cacheDir, "export").apply { mkdirs() }, "photo_${System.currentTimeMillis()}.$ext")
      try {
        val size = PhotoRenderer.render(
          ctx, MediaProbe.parse(uri), temp,
          GradeParams.fromJson(gradeJson), EditTransform.fromJson(transformJson),
          if (format == "png") "png" else "jpeg", quality
        )
        val saved = MediaStoreWriter.saveFile(ctx, temp, MediaStoreWriter.Kind.IMAGE, MediaStoreWriter.newName("IMG", ext, "_EDIT"), mime)
        mapOf(
          "uri" to saved.toString(),
          "width" to size[0],
          "height" to size[1],
          "bytes" to MediaProbe.fileSize(ctx, saved),
          "thumbnail" to MediaProbe.thumbnail(ctx, saved.toString(), 240)
        )
      } finally {
        temp.delete()
      }
    }

    AsyncFunction("exportVideo") { uri: String, gradeJson: String?, transformJson: String?, optionsJson: String?, promise: Promise ->
      val ex = exporter ?: VideoExporter(context).also { exporter = it }
      ex.export(
        uri,
        GradeParams.fromJson(gradeJson),
        EditTransform.fromJson(transformJson),
        VideoExportOptions.fromJson(optionsJson),
        { stage, progress -> sendEvent("onExportProgress", mapOf("stage" to stage, "progress" to progress.toDouble())) },
        { result, error -> if (result != null) promise.resolve(result) else promise.reject("E_EXPORT", error ?: "Export failed", null) }
      )
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("cancelExport") {
      exporter?.cancel()
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("probeMedia") { uri: String ->
      MediaProbe.probe(context, uri)
    }

    AsyncFunction("getThumbnail") { uri: String, size: Int ->
      MediaProbe.thumbnail(context, uri, size.coerceIn(64, 1024))
    }

    AsyncFunction("getVideoFrames") { uri: String, count: Int, height: Int ->
      MediaProbe.frames(context, uri, count.coerceIn(1, 30), height.coerceIn(24, 240))
    }

    AsyncFunction("getStorageInfo") {
      MediaProbe.storage()
    }

    AsyncFunction("setSaveLocation") { location: String ->
      MediaStoreWriter.location = if (location == "pictures") "pictures" else "dcim"
    }

    AsyncFunction("clearCache") {
      MediaProbe.clearCache(context)
    }

    // MediaStore content URIs can be handed to other apps directly with a read grant.
    AsyncFunction("share") { uris: List<String>, mime: String ->
      val activity = appContext.currentActivity ?: throw IllegalStateException("No activity to share from")
      val parsed = ArrayList(uris.map { Uri.parse(it) })
      if (parsed.isEmpty()) return@AsyncFunction false
      val send = if (parsed.size == 1) {
        Intent(Intent.ACTION_SEND).apply { putExtra(Intent.EXTRA_STREAM, parsed[0]) }
      } else {
        Intent(Intent.ACTION_SEND_MULTIPLE).apply { putParcelableArrayListExtra(Intent.EXTRA_STREAM, parsed) }
      }
      send.type = mime
      send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
      send.clipData = ClipData.newRawUri(null, parsed[0]).also { clip ->
        parsed.drop(1).forEach { clip.addItem(ClipData.Item(it)) }
      }
      val chooser = Intent.createChooser(send, null).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
      activity.startActivity(chooser)
      true
    }.runOnQueue(Queues.MAIN)
  }
}
