package com.cameroplus.engine.edit

import android.content.Context
import android.graphics.Matrix
import android.opengl.GLES20
import androidx.media3.common.GlObjectsProvider
import androidx.media3.common.GlTextureInfo
import androidx.media3.common.VideoFrameProcessingException
import androidx.media3.common.util.GlUtil
import androidx.media3.common.util.Size
import androidx.media3.common.util.UnstableApi
import androidx.media3.effect.BaseGlShaderProgram
import androidx.media3.effect.GlEffect
import androidx.media3.effect.GlShaderProgram
import androidx.media3.effect.MatrixTransformation
import com.cameroplus.engine.gl.Affine
import com.cameroplus.engine.gl.DrawFrame
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.gl.GradeProgram
import com.cameroplus.engine.gl.LutTexture
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.looks.LutCache
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.util.concurrent.Executor
import kotlin.math.max
import kotlin.math.roundToInt

/** Minimal shader helper for the small single-purpose effects below. */
internal class SimpleProgram(vertex: String, fragment: String) {
  val id: Int
  private val aPos: Int
  private val quad: FloatBuffer = ByteBuffer.allocateDirect(32).order(ByteOrder.nativeOrder()).asFloatBuffer().apply {
    put(floatArrayOf(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f))
    position(0)
  }

  init {
    fun compile(type: Int, src: String): Int {
      val s = GLES20.glCreateShader(type)
      GLES20.glShaderSource(s, src)
      GLES20.glCompileShader(s)
      val ok = IntArray(1)
      GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0)
      if (ok[0] == 0) throw IllegalStateException("Shader compile failed: " + GLES20.glGetShaderInfoLog(s))
      return s
    }
    val vs = compile(GLES20.GL_VERTEX_SHADER, vertex)
    val fs = compile(GLES20.GL_FRAGMENT_SHADER, fragment)
    id = GLES20.glCreateProgram()
    GLES20.glAttachShader(id, vs)
    GLES20.glAttachShader(id, fs)
    GLES20.glLinkProgram(id)
    val ok = IntArray(1)
    GLES20.glGetProgramiv(id, GLES20.GL_LINK_STATUS, ok, 0)
    if (ok[0] == 0) throw IllegalStateException("Program link failed: " + GLES20.glGetProgramInfoLog(id))
    GLES20.glDeleteShader(vs)
    GLES20.glDeleteShader(fs)
    aPos = GLES20.glGetAttribLocation(id, "aPos")
  }

  fun use() {
    GLES20.glUseProgram(id)
    GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0)
    GLES20.glDisable(GLES20.GL_BLEND)
  }

  fun loc(name: String): Int = GLES20.glGetUniformLocation(id, name)

  fun bindTexture(name: String, unit: Int, texture: Int) {
    GLES20.glActiveTexture(GLES20.GL_TEXTURE0 + unit)
    GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
    GLES20.glUniform1i(loc(name), unit)
  }

  fun drawQuad() {
    quad.position(0)
    GLES20.glVertexAttribPointer(aPos, 2, GLES20.GL_FLOAT, false, 0, quad)
    GLES20.glEnableVertexAttribArray(aPos)
    GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    GLES20.glDisableVertexAttribArray(aPos)
    GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
  }

  fun release() = GLES20.glDeleteProgram(id)

  companion object {
    const val VERTEX = """
attribute vec4 aPos;
varying vec2 vTex;
void main() {
  gl_Position = aPos;
  vTex = aPos.xy * 0.5 + 0.5;
}
"""
    const val COPY = """
precision mediump float;
varying vec2 vTex;
uniform sampler2D uTex;
void main() { gl_FragColor = vec4(texture2D(uTex, vTex).rgb, 1.0); }
"""
  }
}

/** Look + adjustments + crop/rotate/flip for video export, using the shared grading shader. */
@UnstableApi
class GradeGlEffect(private val grade: GradeParams, private val transform: EditTransform) : GlEffect {
  override fun toGlShaderProgram(context: Context, useHdr: Boolean): GlShaderProgram =
    GradeShaderProgram(grade, transform, useHdr)
}

@UnstableApi
internal class GradeShaderProgram(grade: GradeParams, private val transform: EditTransform, useHdr: Boolean) :
  BaseGlShaderProgram(useHdr, 1) {
  private val program = GradeProgram(external = false)
  private val uniforms = grade.uniforms()
  private val lut = LutTexture()
  private val texMatrix = (Affine.FLIP_Y * transform.outputToDisplayed() * Affine.FLIP_Y).toMat4()
  private val posMatrix = Affine.FLIP_Y.toMat4()
  private var inW = 1
  private var inH = 1
  private var outW = 2
  private var outH = 2

  init {
    uniforms.lutKey?.let { key -> LutCache.get(key)?.let { lut.upload(key, uniforms.lutSize, it) } }
  }

  override fun configure(inputWidth: Int, inputHeight: Int): Size {
    inW = inputWidth
    inH = inputHeight
    val size = transform.outputSize(inputWidth, inputHeight)
    outW = size[0]
    outH = size[1]
    return Size(outW, outH)
  }

  override fun drawFrame(inputTexId: Int, presentationTimeUs: Long) {
    program.draw(
      inputTexId, texMatrix, posMatrix, uniforms, lut.texture,
      DrawFrame(outW, outH, 1f / inW, 1f / inH, max(inW, inH).toFloat(), seed = ((presentationTimeUs / 33_333L) % 997L).toFloat())
    )
  }

  override fun release() {
    super.release()
    program.release()
    lut.release()
  }
}

/** Contrast-adaptive sharpening applied after upscaling, so upscaled exports stay crisp without halos. */
@UnstableApi
class SharpenGlEffect(private val amount: Float) : GlEffect {
  override fun toGlShaderProgram(context: Context, useHdr: Boolean): GlShaderProgram = SharpenProgram(amount, useHdr)
}

@UnstableApi
internal class SharpenProgram(private val amount: Float, useHdr: Boolean) : BaseGlShaderProgram(useHdr, 1) {
  private val program = SimpleProgram(SimpleProgram.VERTEX, FRAGMENT)
  private var w = 1
  private var h = 1

  override fun configure(inputWidth: Int, inputHeight: Int): Size {
    w = inputWidth
    h = inputHeight
    return Size(inputWidth, inputHeight)
  }

  override fun drawFrame(inputTexId: Int, presentationTimeUs: Long) {
    program.use()
    program.bindTexture("uTex", 0, inputTexId)
    GLES20.glUniform2f(program.loc("uTexel"), 1f / w, 1f / h)
    GLES20.glUniform1f(program.loc("uAmount"), amount)
    program.drawQuad()
  }

  override fun release() {
    super.release()
    program.release()
  }

  companion object {
    private const val FRAGMENT = """
precision mediump float;
varying vec2 vTex;
uniform sampler2D uTex;
uniform vec2 uTexel;
uniform float uAmount;
void main() {
  vec3 a = texture2D(uTex, vTex + vec2(0.0, -uTexel.y)).rgb;
  vec3 b = texture2D(uTex, vTex + vec2(-uTexel.x, 0.0)).rgb;
  vec3 c = texture2D(uTex, vTex).rgb;
  vec3 d = texture2D(uTex, vTex + vec2(uTexel.x, 0.0)).rgb;
  vec3 e = texture2D(uTex, vTex + vec2(0.0, uTexel.y)).rgb;
  vec3 mn = min(min(min(a, b), min(c, d)), e);
  vec3 mx = max(max(max(a, b), max(c, d)), e);
  vec3 amp = sqrt(clamp(min(mn, 1.0 - mx) / max(mx, vec3(0.0001)), 0.0, 1.0));
  vec3 wgt = amp * (-1.0 / mix(8.0, 5.0, uAmount));
  vec3 res = ((a + b + d + e) * wgt + c) / (1.0 + 4.0 * wgt);
  gl_FragColor = vec4(clamp(res, 0.0, 1.0), 1.0);
}
"""
  }
}

/** Per-frame stabilization warp computed by [Stabilizer]. */
@UnstableApi
class StabilizeTransformation(private val track: Stabilizer.Track) : MatrixTransformation {
  override fun getMatrix(presentationTimeUs: Long): Matrix = track.matrixAt(presentationTimeUs)
}

/**
 * Doubles the frame rate with motion-compensated interpolation (Smooth 60 from 30 fps footage).
 * Block motion is estimated on a small copy of each frame; the in-between frame warps both
 * neighbours halfway along the motion and falls back to a plain blend where they disagree.
 */
@UnstableApi
class InterpolateEffect : GlEffect {
  override fun toGlShaderProgram(context: Context, useHdr: Boolean): GlShaderProgram = FrameInterpolator()
}

@UnstableApi
internal class FrameInterpolator : GlShaderProgram {
  private var inputListener: GlShaderProgram.InputListener = object : GlShaderProgram.InputListener {}
  private var outputListener: GlShaderProgram.OutputListener = object : GlShaderProgram.OutputListener {}
  private var errorListener: GlShaderProgram.ErrorListener = GlShaderProgram.ErrorListener { }
  private var errorExecutor: Executor = Executor { it.run() }

  private val pool = ArrayList<GlTextureInfo>()
  private val free = ArrayDeque<GlTextureInfo>()
  private var prev: GlTextureInfo? = null
  private var hasPrev = false
  private var prevPts = 0L
  private var width = 0
  private var height = 0
  private var copy: SimpleProgram? = null
  private var interp: SimpleProgram? = null
  private var analysisTex = 0
  private var analysisFbo = 0
  private var aw = 0
  private var ah = 0
  private var pixels: ByteBuffer? = null
  private var rgba = ByteArray(0)
  private var prevLuma: ByteArray? = null
  private var motionTex = 0
  private val motionBytes = ByteBuffer.allocateDirect(COLS * ROWS * 4).order(ByteOrder.nativeOrder())
  private var readyOwed = false

  override fun setInputListener(inputListener: GlShaderProgram.InputListener) {
    this.inputListener = inputListener
    inputListener.onReadyToAcceptInputFrame()
  }

  override fun setOutputListener(outputListener: GlShaderProgram.OutputListener) {
    this.outputListener = outputListener
  }

  override fun setErrorListener(executor: Executor, errorListener: GlShaderProgram.ErrorListener) {
    errorExecutor = executor
    this.errorListener = errorListener
  }

  private fun newTexture(provider: GlObjectsProvider, w: Int, h: Int): GlTextureInfo =
    provider.createBuffersForTexture(GlUtil.createTexture(w, h, false), w, h)

  private fun ensure(provider: GlObjectsProvider, w: Int, h: Int) {
    if (w == width && h == height && pool.isNotEmpty()) return
    releaseTextures()
    width = w
    height = h
    repeat(POOL) { pool.add(newTexture(provider, w, h)) }
    free.addAll(pool)
    prev = newTexture(provider, w, h)
    if (copy == null) copy = SimpleProgram(SimpleProgram.VERTEX, SimpleProgram.COPY)
    if (interp == null) interp = SimpleProgram(SimpleProgram.VERTEX, INTERP)
    aw = ANALYSIS_WIDTH
    ah = ((ANALYSIS_WIDTH.toFloat() * h / w).roundToInt() / 2 * 2).coerceIn(32, 256)
    analysisTex = com.cameroplus.engine.gl.GlCore.create2dTexture()
    GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, aw, ah, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
    val ids = IntArray(1)
    GLES20.glGenFramebuffers(1, ids, 0)
    analysisFbo = ids[0]
    GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, analysisFbo)
    GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, analysisTex, 0)
    pixels = ByteBuffer.allocateDirect(aw * ah * 4).order(ByteOrder.nativeOrder())
    rgba = ByteArray(aw * ah * 4)
    motionTex = com.cameroplus.engine.gl.GlCore.create2dTexture()
    hasPrev = false
  }

  private fun analyse(texId: Int): ByteArray {
    val c = copy!!
    GlUtil.focusFramebufferUsingCurrentContext(analysisFbo, aw, ah)
    c.use()
    c.bindTexture("uTex", 0, texId)
    c.drawQuad()
    val buf = pixels!!
    buf.position(0)
    GLES20.glReadPixels(0, 0, aw, ah, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, buf)
    buf.position(0)
    buf.get(rgba)
    val luma = ByteArray(aw * ah)
    MotionEstimator.lumaFromRgba(rgba, aw, ah, luma)
    return luma
  }

  private fun uploadMotion(field: FloatArray) {
    motionBytes.position(0)
    for (i in 0 until COLS * ROWS) {
      val dx = (field[i * 2] / (2f * MAX_MOTION) + 0.5f).coerceIn(0f, 1f)
      val dy = (field[i * 2 + 1] / (2f * MAX_MOTION) + 0.5f).coerceIn(0f, 1f)
      motionBytes.put((dx * 255f + 0.5f).toInt().toByte())
      motionBytes.put((dy * 255f + 0.5f).toInt().toByte())
      motionBytes.put(0)
      motionBytes.put(0xFF.toByte())
    }
    motionBytes.position(0)
    GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, motionTex)
    GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, COLS, ROWS, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, motionBytes)
  }

  override fun queueInputFrame(glObjectsProvider: GlObjectsProvider, inputTexture: GlTextureInfo, presentationTimeUs: Long) {
    try {
      ensure(glObjectsProvider, inputTexture.width, inputTexture.height)
      val luma = analyse(inputTexture.texId)
      val previous = prev!!
      val lastLuma = prevLuma
      if (hasPrev && lastLuma != null && free.isNotEmpty()) {
        val field = MotionEstimator.blockField(lastLuma, luma, aw, ah, BLOCK, COLS, ROWS)
        uploadMotion(field)
        val mid = free.removeFirst()
        GlUtil.focusFramebufferUsingCurrentContext(mid.fboId, mid.width, mid.height)
        val p = interp!!
        p.use()
        p.bindTexture("uPrev", 0, previous.texId)
        p.bindTexture("uCur", 1, inputTexture.texId)
        p.bindTexture("uMotion", 2, motionTex)
        GLES20.glUniform2f(p.loc("uMvScale"), 2f * MAX_MOTION / aw, 2f * MAX_MOTION / ah)
        p.drawQuad()
        outputListener.onOutputFrameAvailable(mid, (prevPts + presentationTimeUs) / 2)
      }
      if (free.isNotEmpty()) {
        val out = free.removeFirst()
        GlUtil.focusFramebufferUsingCurrentContext(out.fboId, out.width, out.height)
        val c = copy!!
        c.use()
        c.bindTexture("uTex", 0, inputTexture.texId)
        c.drawQuad()
        outputListener.onOutputFrameAvailable(out, presentationTimeUs)
      }
      GlUtil.focusFramebufferUsingCurrentContext(previous.fboId, previous.width, previous.height)
      copy!!.apply {
        use()
        bindTexture("uTex", 0, inputTexture.texId)
        drawQuad()
      }
      prevLuma = luma
      prevPts = presentationTimeUs
      hasPrev = true
      inputListener.onInputFrameProcessed(inputTexture)
      if (free.size >= 2) inputListener.onReadyToAcceptInputFrame() else readyOwed = true
    } catch (e: Exception) {
      errorExecutor.execute { errorListener.onError(VideoFrameProcessingException.from(e)) }
    }
  }

  override fun releaseOutputFrame(outputTexture: GlTextureInfo) {
    if (pool.any { it === outputTexture } && free.none { it === outputTexture }) free.addLast(outputTexture)
    if (readyOwed && free.size >= 2) {
      readyOwed = false
      inputListener.onReadyToAcceptInputFrame()
    }
  }

  override fun signalEndOfCurrentInputStream() {
    hasPrev = false
    prevLuma = null
    outputListener.onCurrentOutputStreamEnded()
  }

  override fun flush() {
    free.clear()
    free.addAll(pool)
    hasPrev = false
    prevLuma = null
    readyOwed = false
    inputListener.onFlush()
    inputListener.onReadyToAcceptInputFrame()
  }

  private fun releaseTextures() {
    try {
      pool.forEach { it.release() }
      prev?.release()
    } catch (_: Exception) {
    }
    pool.clear()
    free.clear()
    prev = null
    if (analysisFbo != 0) GLES20.glDeleteFramebuffers(1, intArrayOf(analysisFbo), 0)
    com.cameroplus.engine.gl.GlCore.deleteTexture(analysisTex)
    com.cameroplus.engine.gl.GlCore.deleteTexture(motionTex)
    analysisFbo = 0
    analysisTex = 0
    motionTex = 0
  }

  override fun release() {
    releaseTextures()
    copy?.release()
    interp?.release()
    copy = null
    interp = null
  }

  companion object {
    private const val POOL = 4
    private const val ANALYSIS_WIDTH = 192
    private const val BLOCK = 12
    private const val COLS = 24
    private const val ROWS = 14
    private const val MAX_MOTION = 12f
    private const val INTERP = """
precision mediump float;
varying vec2 vTex;
uniform sampler2D uPrev;
uniform sampler2D uCur;
uniform sampler2D uMotion;
uniform vec2 uMvScale;
void main() {
  vec2 mv = (texture2D(uMotion, vTex).rg - 0.5) * uMvScale;
  vec3 a = texture2D(uPrev, vTex - mv * 0.5).rgb;
  vec3 b = texture2D(uCur, vTex + mv * 0.5).rgb;
  vec3 a0 = texture2D(uPrev, vTex).rgb;
  vec3 b0 = texture2D(uCur, vTex).rgb;
  float diff = length(a - b);
  vec3 warped = mix(a, b, 0.5);
  vec3 blended = mix(a0, b0, 0.5);
  gl_FragColor = vec4(mix(warped, blended, smoothstep(0.1, 0.35, diff)), 1.0);
}
"""
  }
}
