package com.cameroplus.engine.edit

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.media3.common.Effect
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.audio.AudioProcessor
import androidx.media3.common.audio.SpeedProvider
import androidx.media3.common.util.UnstableApi
import androidx.media3.effect.FrameDropEffect
import androidx.media3.effect.Presentation
import androidx.media3.transformer.Composition
import androidx.media3.transformer.DefaultEncoderFactory
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.EditedMediaItemSequence
import androidx.media3.transformer.Effects
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.ProgressHolder
import androidx.media3.transformer.Transformer
import androidx.media3.transformer.VideoEncoderSettings
import com.cameroplus.engine.camera.CameraCatalog
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.media.MediaProbe
import com.cameroplus.engine.media.MediaStoreWriter
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Export settings sent from the video editor. */
data class VideoExportOptions(
  val trimStartMs: Long = 0,
  val trimEndMs: Long = -1,
  val speed: Float = 1f,
  val mute: Boolean = false,
  val resolution: String = "original",
  val fps: Int = 0,
  val smooth: Boolean = false,
  val codec: String = "h264",
  val bitrate: Int = 0,
  val stabilize: Float = -1f
) {
  companion object {
    fun fromJson(json: String?): VideoExportOptions {
      if (json.isNullOrBlank()) return VideoExportOptions()
      val o = JSONObject(json)
      return VideoExportOptions(
        trimStartMs = o.optLong("trimStartMs", 0),
        trimEndMs = o.optLong("trimEndMs", -1),
        speed = o.optDouble("speed", 1.0).toFloat().coerceIn(0.25f, 4f),
        mute = o.optBoolean("mute", false),
        resolution = o.optString("resolution", "original"),
        fps = o.optInt("fps", 0),
        smooth = o.optBoolean("smooth", false),
        codec = o.optString("codec", "h264"),
        bitrate = o.optInt("bitrate", 0),
        stabilize = if (o.has("stabilize") && !o.isNull("stabilize")) o.optDouble("stabilize").toFloat() else -1f
      )
    }
  }
}

/**
 * Exports an edited copy of a video with Media3 Transformer (hardware codecs where available).
 * The source file is never modified; the result is saved as a new item in the gallery.
 */
@UnstableApi
class VideoExporter(private val context: Context) {
  private val main = Handler(Looper.getMainLooper())
  private val worker = Executors.newSingleThreadExecutor()
  private var transformer: Transformer? = null
  @Volatile private var cancelled = false
  private var running = false

  fun cancel() {
    cancelled = true
    main.post { transformer?.cancel() }
  }

  fun export(
    uriString: String,
    grade: GradeParams,
    transform: EditTransform,
    opts: VideoExportOptions,
    onProgress: (String, Float) -> Unit,
    onDone: (Map<String, Any?>?, String?) -> Unit
  ) {
    if (running) {
      onDone(null, "Another export is still running.")
      return
    }
    running = true
    cancelled = false
    val uri = MediaProbe.parse(uriString)
    worker.execute {
      try {
        val info = MediaProbe.probe(context, uriString)
        val srcW = (info["width"] as? Int) ?: 0
        val srcH = (info["height"] as? Int) ?: 0
        val srcFps = ((info["fps"] as? Float) ?: (info["captureFps"] as? Float) ?: 30f)
        val durationMs = (info["durationMs"] as? Long) ?: 0L
        if (srcW <= 0 || srcH <= 0) throw IllegalArgumentException("This video can't be read.")
        val startUs = max(0L, opts.trimStartMs) * 1000L
        val endUs = if (opts.trimEndMs > 0) min(opts.trimEndMs, durationMs) * 1000L else durationMs * 1000L
        val track = if (opts.stabilize >= 0f) {
          Stabilizer.analyze(context, uri, startUs, endUs, opts.stabilize, { p -> main.post { onProgress("analyzing", p) } }, { cancelled })
        } else null
        if (cancelled) throw InterruptedException("Cancelled")
        main.post { startTransformer(uriString, srcW, srcH, srcFps, startUs, endUs, track, grade, transform, opts, onProgress, onDone) }
      } catch (e: InterruptedException) {
        main.post { finish(null, "Export cancelled.", onDone) }
      } catch (e: Throwable) {
        main.post { finish(null, e.message ?: "Export failed.", onDone) }
      }
    }
  }

  private fun finish(result: Map<String, Any?>?, error: String?, onDone: (Map<String, Any?>?, String?) -> Unit) {
    running = false
    transformer = null
    onDone(result, error)
  }

  private fun startTransformer(
    uriString: String,
    srcW: Int,
    srcH: Int,
    srcFps: Float,
    startUs: Long,
    endUs: Long,
    track: Stabilizer.Track?,
    grade: GradeParams,
    transform: EditTransform,
    opts: VideoExportOptions,
    onProgress: (String, Float) -> Unit,
    onDone: (Map<String, Any?>?, String?) -> Unit
  ) {
    val video = ArrayList<Effect>()
    val audio = ArrayList<AudioProcessor>()
    track?.let { video.add(StabilizeTransformation(it)) }
    if (!grade.isNeutral || !transform.isIdentity) video.add(GradeGlEffect(grade, transform))
    val interpolate = opts.smooth && srcFps <= 31f
    if (interpolate) video.add(InterpolateEffect())

    val cropped = transform.outputSize(srcW, srcH)
    val shortSide = min(cropped[0], cropped[1])
    val target = when (opts.resolution) {
      "2160" -> 2160
      "1440" -> 1440
      "1080" -> 1080
      "720" -> 720
      else -> shortSide
    }
    var upscaled = false
    if (target != shortSide) {
      val scale = target.toFloat() / shortSide
      val w = ((cropped[0] * scale).roundToInt() / 2) * 2
      val h = ((cropped[1] * scale).roundToInt() / 2) * 2
      video.add(Presentation.createForWidthAndHeight(w, h, Presentation.LAYOUT_SCALE_TO_FIT))
      if (scale > 1.01f) {
        upscaled = true
        video.add(SharpenGlEffect(0.55f))
      }
    }
    if (opts.fps in 1 until srcFps.roundToInt() && !interpolate) {
      video.add(FrameDropEffect.createDefaultFrameDropEffect(opts.fps.toFloat()))
    }
    if (opts.speed != 1f) {
      val speed = opts.speed
      val pair = Effects.createExperimentalSpeedChangingEffect(object : SpeedProvider {
        override fun getSpeed(timeUs: Long): Float = speed
        override fun getNextSpeedChangeTimeUs(timeUs: Long): Long = androidx.media3.common.C.TIME_UNSET
      })
      audio.add(pair.first)
      video.add(pair.second)
    }

    val clipping = MediaItem.ClippingConfiguration.Builder()
      .setStartPositionMs(startUs / 1000)
      .apply { if (endUs > startUs) setEndPositionMs(endUs / 1000) }
      .build()
    val mediaItem = MediaItem.Builder().setUri(MediaProbe.parse(uriString)).setClippingConfiguration(clipping).build()
    val edited = EditedMediaItem.Builder(mediaItem)
      .setRemoveAudio(opts.mute)
      .setEffects(Effects(audio, video))
      .build()
    val composition = Composition.Builder(EditedMediaItemSequence(listOf(edited)))
      .setHdrMode(Composition.HDR_MODE_TONE_MAP_HDR_TO_SDR_USING_OPEN_GL)
      .build()

    val hevc = opts.codec == "hevc" && CameraCatalog.hevcEncoderAvailable()
    val outW = if (target != shortSide) ((cropped[0] * target.toFloat() / shortSide).roundToInt()) else cropped[0]
    val outH = if (target != shortSide) ((cropped[1] * target.toFloat() / shortSide).roundToInt()) else cropped[1]
    val outFps = if (interpolate) srcFps * 2f else if (opts.fps > 0) min(opts.fps.toFloat(), srcFps) else srcFps
    val bitrate = if (opts.bitrate > 0) opts.bitrate else defaultBitrate(outW, outH, outFps, hevc)
    val encoderFactory = DefaultEncoderFactory.Builder(context)
      .setRequestedVideoEncoderSettings(VideoEncoderSettings.Builder().setBitrate(bitrate).build())
      .setEnableFallback(true)
      .build()
    val tempDir = File(context.cacheDir, "export").apply { mkdirs() }
    val temp = File(tempDir, "export_${System.currentTimeMillis()}.mp4")
    val hasStabilization = track != null

    val listener = object : Transformer.Listener {
      override fun onCompleted(composition: Composition, exportResult: ExportResult) {
        worker.execute {
          try {
            val name = MediaStoreWriter.newName("VID", "mp4", "_EDIT")
            val saved = MediaStoreWriter.saveFile(context, temp, MediaStoreWriter.Kind.VIDEO, name, "video/mp4")
            temp.delete()
            val probe = MediaProbe.probe(context, saved.toString())
            val gotW = (probe["width"] as? Int) ?: 0
            val gotH = (probe["height"] as? Int) ?: 0
            val warning = if (target != shortSide && min(gotW, gotH) + 8 < target) {
              "This phone's video encoder couldn't write ${target}p, so the file was saved at ${min(gotW, gotH)}p."
            } else null
            val thumb = MediaProbe.thumbnail(context, saved.toString(), 240)
            val result = mapOf(
              "uri" to saved.toString(),
              "thumbnail" to thumb,
              "width" to gotW,
              "height" to gotH,
              "durationMs" to probe["durationMs"],
              "bytes" to probe["bytes"],
              "upscaled" to upscaled,
              "interpolated" to interpolate,
              "stabilized" to hasStabilization,
              "codec" to if (hevc) "hevc" else "h264",
              "warning" to warning
            )
            main.post { finish(result, null, onDone) }
          } catch (e: Exception) {
            main.post { finish(null, "The video was rendered but couldn't be saved: ${e.message}", onDone) }
          }
        }
      }

      override fun onError(composition: Composition, exportResult: ExportResult, exportException: ExportException) {
        temp.delete()
        val message = if (cancelled) "Export cancelled." else (exportException.message ?: "Export failed.")
        finish(null, message, onDone)
      }
    }

    val t = Transformer.Builder(context)
      .setVideoMimeType(if (hevc) MimeTypes.VIDEO_H265 else MimeTypes.VIDEO_H264)
      .setAudioMimeType(MimeTypes.AUDIO_AAC)
      .setEncoderFactory(encoderFactory)
      .addListener(listener)
      .build()
    transformer = t
    try {
      t.start(composition, temp.absolutePath)
    } catch (e: Exception) {
      finish(null, e.message ?: "Export couldn't start.", onDone)
      return
    }
    val holder = ProgressHolder()
    val base = if (hasStabilization) 0.3f else 0f
    val poll = object : Runnable {
      override fun run() {
        val current = transformer ?: return
        if (current !== t) return
        val state = t.getProgress(holder)
        if (state == Transformer.PROGRESS_STATE_AVAILABLE) {
          onProgress("rendering", base + (1f - base) * holder.progress / 100f)
        }
        if (state != Transformer.PROGRESS_STATE_NOT_STARTED || running) main.postDelayed(this, 250)
      }
    }
    main.postDelayed(poll, 250)
  }

  private fun defaultBitrate(w: Int, h: Int, fps: Float, hevc: Boolean): Int {
    val pixelsPerSecond = w.toLong() * h * max(fps, 24f)
    val bpp = if (hevc) 0.07 else 0.11
    return (pixelsPerSecond * bpp).toLong().coerceIn(2_000_000L, 100_000_000L).toInt()
  }
}
