package com.cameroplus.engine.edit

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Post-recording stabilization. Decodes the clip with the hardware decoder, measures frame-to-frame
 * motion on a small luma copy, smooths the camera path and returns a per-frame warp. Works on any
 * phone; the result is cropped by [Track.zoom] to hide moving edges. The original file is untouched.
 */
object Stabilizer {
  class Track(
    private val timesUs: LongArray,
    private val dx: FloatArray,
    private val dy: FloatArray,
    private val angle: FloatArray,
    val zoom: Float,
    private val startUs: Long,
    private val aspect: Float
  ) {
    private var offsetUs: Long? = null

    /** Warp for the frame at [ptsUs], in normalized device coordinates for Media3. */
    fun matrixAt(ptsUs: Long): Matrix {
      if (offsetUs == null) {
        offsetUs = if (startUs > 0 && abs(ptsUs - startUs) > abs(ptsUs)) startUs else 0L
      }
      val t = ptsUs + (offsetUs ?: 0L)
      var lo = 0
      var hi = timesUs.size - 1
      if (hi < 0) return Matrix().apply { setScale(zoom, zoom) }
      while (lo < hi) {
        val mid = (lo + hi) / 2
        if (timesUs[mid] < t) lo = mid + 1 else hi = mid
      }
      val i = if (lo > 0 && abs(timesUs[lo - 1] - t) < abs(timesUs[lo] - t)) lo - 1 else lo
      val m = Matrix()
      m.setScale(aspect, 1f)
      m.postRotate((-angle[i] * 180.0 / PI).toFloat())
      m.postScale(1f / aspect, 1f)
      m.postScale(zoom, zoom)
      m.postTranslate(dx[i] * 2f, -dy[i] * 2f)
      return m
    }
  }

  /**
   * Analyses [uri] between [startUs] and [endUs]. [strength] 0..1 sets smoothing and crop.
   * Rotation-aware: measurements are converted to the clip's display orientation.
   */
  fun analyze(
    context: Context,
    uri: Uri,
    startUs: Long,
    endUs: Long,
    strength: Float,
    onProgress: (Float) -> Unit,
    isCancelled: () -> Boolean
  ): Track {
    val extractor = MediaExtractor()
    extractor.setDataSource(context, uri, null)
    var trackIndex = -1
    var format: MediaFormat? = null
    for (i in 0 until extractor.trackCount) {
      val f = extractor.getTrackFormat(i)
      if (f.getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true) {
        trackIndex = i
        format = f
        break
      }
    }
    if (trackIndex < 0 || format == null) {
      extractor.release()
      throw IllegalArgumentException("No video track found")
    }
    extractor.selectTrack(trackIndex)
    val mime = format.getString(MediaFormat.KEY_MIME)!!
    val rotation = if (format.containsKey(MediaFormat.KEY_ROTATION)) format.getInteger(MediaFormat.KEY_ROTATION) else 0
    val durationUs = if (format.containsKey(MediaFormat.KEY_DURATION)) format.getLong(MediaFormat.KEY_DURATION) else 0L
    val end = if (endUs > 0) endUs else durationUs
    format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
    val decoder = MediaCodec.createDecoderByType(mime)
    decoder.configure(format, null, null, 0)
    decoder.start()
    extractor.seekTo(startUs, MediaExtractor.SEEK_TO_PREVIOUS_SYNC)

    val times = ArrayList<Long>()
    val motions = ArrayList<MotionEstimator.Motion>()
    var prevLuma: ByteArray? = null
    var aw = 0
    var ah = 0
    val info = MediaCodec.BufferInfo()
    var inputDone = false
    var outputDone = false
    try {
      while (!outputDone) {
        if (isCancelled()) throw InterruptedException("Cancelled")
        if (!inputDone) {
          val inIndex = decoder.dequeueInputBuffer(10_000)
          if (inIndex >= 0) {
            val buffer = decoder.getInputBuffer(inIndex)!!
            val size = extractor.readSampleData(buffer, 0)
            val time = extractor.sampleTime
            if (size < 0 || time > end + 100_000) {
              decoder.queueInputBuffer(inIndex, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
              inputDone = true
            } else {
              decoder.queueInputBuffer(inIndex, 0, size, time, 0)
              extractor.advance()
            }
          }
        }
        val outIndex = decoder.dequeueOutputBuffer(info, 10_000)
        if (outIndex >= 0) {
          val pts = info.presentationTimeUs
          if (info.size > 0 && pts >= startUs - 1000 && pts <= end) {
            val image = decoder.getOutputImage(outIndex)
            if (image != null) {
              if (image.format == ImageFormat.YUV_420_888 || image.planes.isNotEmpty()) {
                val crop = image.cropRect
                val cw = crop.width()
                val ch = crop.height()
                if (aw == 0) {
                  aw = ANALYSIS_WIDTH
                  ah = max(32, (ANALYSIS_WIDTH.toFloat() * ch / cw).roundToInt())
                }
                val plane = image.planes[0]
                val buf = plane.buffer
                val rowStride = plane.rowStride
                val pixStride = plane.pixelStride
                val luma = ByteArray(aw * ah)
                for (y in 0 until ah) {
                  val sy = crop.top + (y * ch / ah)
                  for (x in 0 until aw) {
                    val sx = crop.left + (x * cw / aw)
                    luma[y * aw + x] = buf.get(sy * rowStride + sx * pixStride)
                  }
                }
                val prev = prevLuma
                if (prev != null) {
                  motions.add(MotionEstimator.globalMotion(prev, luma, aw, ah, 8))
                } else {
                  motions.add(MotionEstimator.Motion.NONE)
                }
                times.add(pts)
                prevLuma = luma
              }
              image.close()
            }
            if (end > startUs) onProgress(((pts - startUs).toFloat() / (end - startUs)).coerceIn(0f, 1f))
          }
          decoder.releaseOutputBuffer(outIndex, false)
          if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) outputDone = true
        }
      }
    } finally {
      try { decoder.stop() } catch (_: Exception) {}
      decoder.release()
      extractor.release()
    }
    return buildTrack(times, motions, aw.toFloat(), ah.toFloat(), rotation, strength.coerceIn(0f, 1f), startUs)
  }

  private fun buildTrack(
    times: List<Long>,
    motions: List<MotionEstimator.Motion>,
    aw: Float,
    ah: Float,
    rotation: Int,
    strength: Float,
    startUs: Long
  ): Track {
    val n = times.size
    val zoom = 1.06f + 0.1f * strength
    val rotated = (((rotation % 360) + 360) % 360) == 90 || (((rotation % 360) + 360) % 360) == 270
    val aspect = if (aw <= 0f || ah <= 0f) 16f / 9f else if (rotated) ah / aw else aw / ah
    if (n == 0 || aw <= 0f) return Track(LongArray(0), FloatArray(0), FloatArray(0), FloatArray(0), zoom, startUs, aspect)
    // Cumulative path in normalized units of the display-oriented frame (y down).
    val px = FloatArray(n)
    val py = FloatArray(n)
    val pa = FloatArray(n)
    var cx = 0f
    var cy = 0f
    var ca = 0f
    for (i in 0 until n) {
      val m = motions[i]
      if (m.confidence >= 0.2f) {
        var ux = m.dx / aw
        var uy = m.dy / ah
        when (((rotation % 360) + 360) % 360) {
          90 -> { val t = ux; ux = -uy; uy = t }
          180 -> { ux = -ux; uy = -uy }
          270 -> { val t = ux; ux = uy; uy = -t }
        }
        cx += ux; cy += uy; ca += m.angle
      }
      px[i] = cx; py[i] = cy; pa[i] = ca
    }
    val fps = if (n > 1) (n - 1) * 1_000_000f / max(1L, times[n - 1] - times[0]) else 30f
    val sigma = (0.35f + 0.9f * strength) * fps
    val sx = gaussian(px, sigma)
    val sy = gaussian(py, sigma)
    val sa = gaussian(pa, sigma)
    val margin = (zoom - 1f) / 2f * 0.9f
    val dx = FloatArray(n)
    val dy = FloatArray(n)
    val da = FloatArray(n)
    for (i in 0 until n) {
      dx[i] = (sx[i] - px[i]).coerceIn(-margin, margin)
      dy[i] = (sy[i] - py[i]).coerceIn(-margin, margin)
      da[i] = (sa[i] - pa[i]).coerceIn(-0.035f, 0.035f)
    }
    return Track(times.toLongArray(), dx, dy, da, zoom, startUs, aspect)
  }

  private fun gaussian(v: FloatArray, sigma: Float): FloatArray {
    val n = v.size
    val radius = min(n, (sigma * 3f).roundToInt().coerceAtLeast(1))
    val kernel = FloatArray(radius * 2 + 1) { k ->
      val x = (k - radius).toFloat()
      exp(-(x * x) / (2f * sigma * sigma))
    }
    val out = FloatArray(n)
    for (i in 0 until n) {
      var sum = 0f
      var wsum = 0f
      for (k in -radius..radius) {
        val j = (i + k).coerceIn(0, n - 1)
        val w = kernel[k + radius]
        sum += v[j] * w
        wsum += w
      }
      out[i] = sum / wsum
    }
    return out
  }

  private const val ANALYSIS_WIDTH = 192
}
