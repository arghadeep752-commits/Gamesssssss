package com.cameroplus.engine.camera

import android.graphics.SurfaceTexture
import android.opengl.EGL14
import android.opengl.EGLSurface
import android.opengl.GLES20
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.view.Surface
import androidx.camera.core.CameraEffect
import androidx.camera.core.SurfaceOutput
import androidx.camera.core.SurfaceProcessor
import androidx.camera.core.SurfaceRequest
import com.cameroplus.engine.edit.MotionEstimator
import com.cameroplus.engine.gl.Affine
import com.cameroplus.engine.gl.DrawFrame
import com.cameroplus.engine.gl.GlCore
import com.cameroplus.engine.gl.GradeProgram
import com.cameroplus.engine.gl.LutTexture
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.looks.GradeUniforms
import com.cameroplus.engine.looks.LutCache
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.Executor
import java.util.concurrent.Executors
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.roundToInt
import kotlin.math.sign

/** Viewfinder-only overlays. They are never drawn into recordings. */
data class OverlayState(
  val peaking: Boolean = false,
  val zebra: Boolean = false,
  val bypass: Boolean = false,
  val peakColor: FloatArray = DrawFrame.PEAK_DEFAULT
)

/**
 * CameraX surface processor that runs the grading shader on every camera frame and writes the
 * result to each output (viewfinder, video encoder and the optional time-lapse encoder).
 * It also performs live software stabilization: global motion is measured on a small thumbnail of
 * each frame and compensated with a 10% crop, so it works on phones without OIS, EIS or a gyroscope.
 */
class GradeSurfaceProcessor(private val onGlError: (String) -> Unit) : SurfaceProcessor, SurfaceTexture.OnFrameAvailableListener {
  private val thread = HandlerThread("CameroGrade").apply { start() }
  private val handler = Handler(thread.looper)
  val executor: Executor = Executor { r -> if (!handler.post(r)) Log.w(TAG, "GL thread gone") }
  private val lutExecutor = Executors.newSingleThreadExecutor()

  private var core: GlCore? = null
  private var program: GradeProgram? = null
  private var oesTexture = 0
  private val lut = LutTexture()
  private var inputTexture: SurfaceTexture? = null
  private var inputWidth = 1
  private var inputHeight = 1

  private class Target(val surface: Surface, var egl: EGLSurface, val width: Int, val height: Int, val targets: Int)

  private val outputs = LinkedHashMap<SurfaceOutput, Target>()
  private val stMatrix = FloatArray(16)
  private val outMatrix = FloatArray(16)
  private val identity = Affine.IDENTITY.toMat4()

  @Volatile private var uniforms: GradeUniforms = GradeUniforms.NEUTRAL
  @Volatile private var requestedLook: String? = null
  @Volatile var overlay: OverlayState = OverlayState()
  @Volatile var gradeRecording: Boolean = true
  @Volatile private var stabilize = false
  @Volatile private var released = false
  private var failed = false
  private var frameCounter = 0L

  // Live stabilization state (GL thread only).
  private var thumbFbo = 0
  private var thumbTex = 0
  private var thumbW = 0
  private var thumbH = 0
  private var thumbPixels: ByteBuffer? = null
  private var thumbRgba = ByteArray(0)
  private var prevLuma: ByteArray? = null
  private var curLuma = ByteArray(0)
  private var lastFrameNs = 0L
  private var trajX = 0f
  private var trajY = 0f
  private var trajA = 0f
  private var smoothX = 0f
  private var smoothY = 0f
  private var smoothA = 0f
  private var stabilizerMap: Affine? = null

  var timelapse: TimelapseEncoder? = null
    private set

  init {
    handler.post {
      try {
        core = GlCore(recordable = true)
        program = GradeProgram(external = true)
        oesTexture = GlCore.createOesTexture()
      } catch (e: Exception) {
        failed = true
        onGlError("GPU pipeline unavailable: ${e.message}")
      }
    }
  }

  val isHealthy: Boolean get() = !failed

  fun setGrade(params: GradeParams) {
    val next = params.uniforms()
    val key = next.lutKey
    requestedLook = key
    if (key == null) {
      uniforms = next
      return
    }
    handler.post {
      if (lut.key == key) {
        uniforms = next
      } else {
        lutExecutor.execute {
          val data = LutCache.get(key) ?: return@execute
          handler.post {
            if (released || requestedLook != key) return@post
            try {
              core?.makeCurrentPbuffer()
              lut.upload(key, next.lutSize, data)
              uniforms = next
            } catch (e: Exception) {
              Log.w(TAG, "LUT upload failed", e)
            }
          }
        }
      }
    }
  }

  fun setStabilization(enabled: Boolean) {
    if (stabilize == enabled) return
    stabilize = enabled
    handler.post { resetStabilization() }
  }

  private fun resetStabilization() {
    prevLuma = null
    trajX = 0f; trajY = 0f; trajA = 0f
    smoothX = 0f; smoothY = 0f; smoothA = 0f
    lastFrameNs = 0L
    stabilizerMap = null
  }

  override fun onInputSurface(request: SurfaceRequest) {
    if (released || failed || core == null) {
      request.willNotProvideSurface()
      return
    }
    val size = request.resolution
    val st = SurfaceTexture(oesTexture)
    st.setDefaultBufferSize(size.width, size.height)
    val surface = Surface(st)
    inputWidth = size.width
    inputHeight = size.height
    resetStabilization()
    request.provideSurface(surface, executor) {
      st.setOnFrameAvailableListener(null)
      st.release()
      surface.release()
      if (inputTexture === st) inputTexture = null
    }
    st.setOnFrameAvailableListener(this, handler)
    inputTexture = st
  }

  override fun onOutputSurface(surfaceOutput: SurfaceOutput) {
    if (released || failed) {
      surfaceOutput.close()
      return
    }
    val surface = surfaceOutput.getSurface(executor) {
      outputs.remove(surfaceOutput)?.let { target -> core?.destroySurface(target.egl) }
      surfaceOutput.close()
    }
    val egl = try {
      core?.createWindowSurface(surface) ?: EGL14.EGL_NO_SURFACE
    } catch (e: Exception) {
      Log.w(TAG, "Output surface rejected", e)
      EGL14.EGL_NO_SURFACE
    }
    outputs[surfaceOutput] = Target(surface, egl, surfaceOutput.size.width, surfaceOutput.size.height, surfaceOutput.targets)
  }

  override fun onFrameAvailable(st: SurfaceTexture) {
    if (released) return
    val c = core ?: return
    val p = program ?: return
    try {
      c.makeCurrentPbuffer()
      st.updateTexImage()
      st.getTransformMatrix(stMatrix)
      val timestamp = st.timestamp
      val grade = uniforms
      val ov = overlay
      val lutTex = if (grade.lutKey != null && lut.key == grade.lutKey) lut.texture else 0
      frameCounter++
      val seed = (frameCounter % 997).toFloat()
      val longEdge = maxOf(inputWidth, inputHeight).toFloat()
      val stab = if (stabilize) measureAndStabilize(p, timestamp, longEdge) else null
      val stA = Affine.fromMat4(stMatrix)
      for ((output, target) in outputs) {
        if (target.egl == EGL14.EGL_NO_SURFACE) continue
        output.updateTransformMatrix(outMatrix, stMatrix)
        val texMatrix = if (stab != null) {
          val additional = stA.inverse() * Affine.fromMat4(outMatrix)
          (stA * stab * additional).toMat4()
        } else outMatrix
        if (!c.makeCurrent(target.egl)) continue
        GLES20.glViewport(0, 0, target.width, target.height)
        val preview = (target.targets and CameraEffect.PREVIEW) != 0
        val graded = preview || gradeRecording
        p.draw(
          oesTexture, texMatrix, identity, if (graded) grade else GradeUniforms.NEUTRAL, if (graded) lutTex else 0,
          DrawFrame(
            outWidth = target.width,
            outHeight = target.height,
            texelW = 1f / inputWidth,
            texelH = 1f / inputHeight,
            sourceLongEdge = longEdge,
            peaking = preview && ov.peaking,
            zebra = preview && ov.zebra,
            bypass = preview && ov.bypass,
            peakColor = ov.peakColor,
            seed = seed
          )
        )
        c.setPresentationTime(target.egl, timestamp)
        c.swap(target.egl)
      }
      timelapse?.let { tl ->
        if (tl.shouldCapture(timestamp) && c.makeCurrent(tl.eglSurface)) {
          GLES20.glViewport(0, 0, tl.width, tl.height)
          val m = if (stab != null) (stA * stab).toMat4() else stMatrix
          p.draw(oesTexture, m, identity, grade, lutTex, DrawFrame(tl.width, tl.height, 1f / inputWidth, 1f / inputHeight, longEdge, seed = seed))
          c.setPresentationTime(tl.eglSurface, tl.nextPresentationNs())
          c.swap(tl.eglSurface)
          tl.onFrameWritten(timestamp)
        }
      }
    } catch (e: Exception) {
      Log.w(TAG, "Frame failed", e)
    }
  }

  private fun ensureThumbnail() {
    val w = THUMB_WIDTH
    val h = ((THUMB_WIDTH.toFloat() * inputHeight / inputWidth).roundToInt()).coerceIn(32, 192)
    if (thumbFbo != 0 && w == thumbW && h == thumbH) return
    if (thumbFbo != 0) {
      GLES20.glDeleteFramebuffers(1, intArrayOf(thumbFbo), 0)
      GlCore.deleteTexture(thumbTex)
    }
    thumbW = w
    thumbH = h
    thumbTex = GlCore.create2dTexture()
    GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, w, h, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
    val ids = IntArray(1)
    GLES20.glGenFramebuffers(1, ids, 0)
    thumbFbo = ids[0]
    GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, thumbFbo)
    GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, thumbTex, 0)
    GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
    thumbPixels = ByteBuffer.allocateDirect(w * h * 4).order(ByteOrder.nativeOrder())
    thumbRgba = ByteArray(w * h * 4)
    curLuma = ByteArray(w * h)
    prevLuma = null
  }

  /** Measures global motion on a thumbnail and returns the compensating map (buffer uv -> buffer uv). */
  private fun measureAndStabilize(p: GradeProgram, timestampNs: Long, longEdge: Float): Affine? {
    ensureThumbnail()
    GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, thumbFbo)
    GLES20.glViewport(0, 0, thumbW, thumbH)
    p.draw(
      oesTexture, stMatrix, identity, GradeUniforms.NEUTRAL, 0,
      DrawFrame(thumbW, thumbH, 1f / inputWidth, 1f / inputHeight, longEdge, bypass = true)
    )
    val pixels = thumbPixels ?: return stabilizerMap
    pixels.position(0)
    GLES20.glReadPixels(0, 0, thumbW, thumbH, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, pixels)
    GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
    pixels.position(0)
    pixels.get(thumbRgba)
    val cur = curLuma
    MotionEstimator.lumaFromRgba(thumbRgba, thumbW, thumbH, cur)
    val prev = prevLuma
    val dt = if (lastFrameNs > 0L) ((timestampNs - lastFrameNs) / 1e9f).coerceIn(0.004f, 0.2f) else 1f / 30f
    lastFrameNs = timestampNs
    if (prev != null) {
      val m = MotionEstimator.globalMotion(prev, cur, thumbW, thumbH)
      if (m.confidence < 0.2f) {
        smoothX = trajX; smoothY = trajY; smoothA = trajA
      } else {
        trajX += m.dx / thumbW
        trajY += m.dy / thumbH
        trajA += m.angle
        val alpha = exp(-dt / SMOOTH_SECONDS)
        smoothX = smoothX * alpha + trajX * (1f - alpha)
        smoothY = smoothY * alpha + trajY * (1f - alpha)
        smoothA = smoothA * alpha + trajA * (1f - alpha)
      }
    }
    // Reuse buffers: the current frame becomes the previous one.
    prevLuma = cur
    curLuma = prev ?: ByteArray(thumbW * thumbH)

    val maxShift = (1f - 1f / ZOOM) / 2f * 0.85f
    var corrX = smoothX - trajX
    var corrY = smoothY - trajY
    var corrA = smoothA - trajA
    if (abs(corrX) > maxShift) { corrX = sign(corrX) * maxShift; smoothX = trajX + corrX }
    if (abs(corrY) > maxShift) { corrY = sign(corrY) * maxShift; smoothY = trajY + corrY }
    if (abs(corrA) > MAX_ANGLE) { corrA = sign(corrA) * MAX_ANGLE; smoothA = trajA + corrA }
    val map = Affine.stabilizer(inputWidth.toFloat(), inputHeight.toFloat(), ZOOM, -corrX, -corrY, -corrA)
    stabilizerMap = map
    return map
  }

  /** Starts writing graded frames into a new MP4. Runs on the GL thread. */
  fun startTimelapse(factory: (GlCore) -> TimelapseEncoder, onStarted: (Throwable?) -> Unit) {
    handler.post {
      val c = core
      if (c == null || inputTexture == null) {
        onStarted(IllegalStateException("Camera is not streaming yet"))
        return@post
      }
      try {
        timelapse = factory(c)
        onStarted(null)
      } catch (e: Exception) {
        onStarted(e)
      }
    }
  }

  fun stopTimelapse(onStopped: (TimelapseEncoder.Result?) -> Unit) {
    handler.post {
      val tl = timelapse
      timelapse = null
      if (tl == null) {
        onStopped(null)
        return@post
      }
      val result = try {
        tl.finish(core)
      } catch (e: Exception) {
        Log.w(TAG, "Time-lapse finish failed", e)
        null
      }
      onStopped(result)
    }
  }

  val inputSize: IntArray get() = intArrayOf(inputWidth, inputHeight)

  /** Releases GL resources once CameraX has let go of the surfaces. */
  fun release() {
    if (released) return
    released = true
    handler.post {
      try {
        timelapse?.finish(core)
      } catch (_: Exception) {
      }
      timelapse = null
      outputs.forEach { (output, target) ->
        core?.destroySurface(target.egl)
        output.close()
      }
      outputs.clear()
      inputTexture?.setOnFrameAvailableListener(null)
      try {
        core?.makeCurrentPbuffer()
        lut.release()
        program?.release()
        GlCore.deleteTexture(oesTexture)
        if (thumbFbo != 0) GLES20.glDeleteFramebuffers(1, intArrayOf(thumbFbo), 0)
        GlCore.deleteTexture(thumbTex)
      } catch (_: Exception) {
      }
      core?.release()
      core = null
      program = null
    }
    handler.postDelayed({ thread.quitSafely() }, 1500)
    lutExecutor.shutdown()
  }

  companion object {
    private const val TAG = "CameroGrade"
    private const val THUMB_WIDTH = 128
    const val ZOOM = 1.1f
    private const val SMOOTH_SECONDS = 0.45f
    private const val MAX_ANGLE = 0.03f
  }
}
