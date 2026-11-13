package com.cameroplus.engine.camera

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
import android.opengl.EGLSurface
import android.os.ParcelFileDescriptor
import android.view.Surface
import com.cameroplus.engine.gl.GlCore

/**
 * Encodes one graded camera frame every [intervalNs] into an H.264 MP4 played back at 30 fps.
 * Owned by the GL thread of [GradeSurfaceProcessor]. Audio is intentionally absent.
 */
class TimelapseEncoder(
  core: GlCore,
  requestedWidth: Int,
  requestedHeight: Int,
  orientationHint: Int,
  private val intervalNs: Long,
  val uri: Uri,
  private val pfd: ParcelFileDescriptor
) {
  class Result(val uri: Uri, val frames: Int, val durationMs: Long, val ok: Boolean)

  val width: Int = (requestedWidth / 16) * 16
  val height: Int = (requestedHeight / 16) * 16
  private val codec: MediaCodec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
  private val inputSurface: Surface
  val eglSurface: EGLSurface
  private val muxer: MediaMuxer
  private val info = MediaCodec.BufferInfo()
  private var track = -1
  private var muxerStarted = false
  private var lastCaptureNs = -1L
  private var frames = 0

  init {
    val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height).apply {
      setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
      setInteger(MediaFormat.KEY_BIT_RATE, (width * height * 30 * 0.18).toInt().coerceIn(4_000_000, 40_000_000))
      setInteger(MediaFormat.KEY_FRAME_RATE, FPS)
      setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
    }
    codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
    inputSurface = codec.createInputSurface()
    codec.start()
    eglSurface = core.createWindowSurface(inputSurface)
    muxer = MediaMuxer(pfd.fileDescriptor, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
    muxer.setOrientationHint(orientationHint)
  }

  fun shouldCapture(timestampNs: Long): Boolean = lastCaptureNs < 0 || timestampNs - lastCaptureNs >= intervalNs

  fun nextPresentationNs(): Long = frames * 1_000_000_000L / FPS

  val frameCount: Int get() = frames

  fun onFrameWritten(timestampNs: Long) {
    lastCaptureNs = timestampNs
    frames++
    drain(false)
  }

  private fun drain(endOfStream: Boolean) {
    var idleLoops = 0
    while (true) {
      val index = codec.dequeueOutputBuffer(info, if (endOfStream) 10_000L else 0L)
      when {
        index == MediaCodec.INFO_TRY_AGAIN_LATER -> {
          if (!endOfStream || ++idleLoops > 200) return
        }
        index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
          if (!muxerStarted) {
            track = muxer.addTrack(codec.outputFormat)
            muxer.start()
            muxerStarted = true
          }
        }
        index >= 0 -> {
          val buffer = codec.getOutputBuffer(index)
          if (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) info.size = 0
          if (buffer != null && info.size > 0 && muxerStarted) {
            buffer.position(info.offset)
            buffer.limit(info.offset + info.size)
            muxer.writeSampleData(track, buffer, info)
          }
          codec.releaseOutputBuffer(index, false)
          if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
        }
      }
    }
  }

  fun finish(core: GlCore?): Result {
    var ok = frames > 0
    try {
      codec.signalEndOfInputStream()
      drain(true)
    } catch (e: Exception) {
      ok = false
    }
    try { codec.stop() } catch (_: Exception) {}
    codec.release()
    try {
      if (muxerStarted) muxer.stop() else ok = false
    } catch (e: Exception) {
      ok = false
    }
    try { muxer.release() } catch (_: Exception) {}
    core?.destroySurface(eglSurface)
    inputSurface.release()
    try { pfd.close() } catch (_: Exception) {}
    return Result(uri, frames, frames * 1000L / FPS, ok)
  }

  companion object {
    const val FPS = 30
  }
}
