package com.cameroplus.engine.gl

import android.opengl.GLES11Ext
import android.opengl.GLES20
import com.cameroplus.engine.looks.GradeUniforms
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

/** Per-draw values that are not part of the grade itself. */
class DrawFrame(
  val outWidth: Int,
  val outHeight: Int,
  val texelW: Float,
  val texelH: Float,
  val sourceLongEdge: Float,
  val detailScale: Float = 1f,
  val peaking: Boolean = false,
  val zebra: Boolean = false,
  val bypass: Boolean = false,
  val peakColor: FloatArray = PEAK_DEFAULT,
  val seed: Float = 0f
) {
  companion object {
    val PEAK_DEFAULT = floatArrayOf(1f, 0.706f, 0.42f)
  }
}

/** Compiles and draws the grading shader. Must be created and used on one GL thread. */
class GradeProgram(private val external: Boolean) {
  private val program: Int
  private val aPos: Int
  private val uTexMatrix: Int
  private val uPosMatrix: Int
  private val uTex: Int
  private val uLut: Int
  private val uLutParams: Int
  private val uTone: Int
  private val uTone2: Int
  private val uTone3: Int
  private val uDetail: Int
  private val uWb: Int
  private val uFrame: Int
  private val uTexel: Int
  private val uOverlay: Int
  private val uPeakColor: Int

  private val quad: FloatBuffer = ByteBuffer.allocateDirect(8 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply {
    put(floatArrayOf(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f))
    position(0)
  }

  init {
    val vs = compile(GLES20.GL_VERTEX_SHADER, Shaders.VERTEX)
    val fs = compile(GLES20.GL_FRAGMENT_SHADER, if (external) Shaders.FRAGMENT_OES else Shaders.FRAGMENT_2D)
    program = GLES20.glCreateProgram()
    GLES20.glAttachShader(program, vs)
    GLES20.glAttachShader(program, fs)
    GLES20.glLinkProgram(program)
    val status = IntArray(1)
    GLES20.glGetProgramiv(program, GLES20.GL_LINK_STATUS, status, 0)
    if (status[0] == 0) {
      val log = GLES20.glGetProgramInfoLog(program)
      GLES20.glDeleteProgram(program)
      throw IllegalStateException("Grade shader link failed: $log")
    }
    GLES20.glDeleteShader(vs)
    GLES20.glDeleteShader(fs)
    aPos = GLES20.glGetAttribLocation(program, "aPos")
    uTexMatrix = GLES20.glGetUniformLocation(program, "uTexMatrix")
    uPosMatrix = GLES20.glGetUniformLocation(program, "uPosMatrix")
    uTex = GLES20.glGetUniformLocation(program, "uTex")
    uLut = GLES20.glGetUniformLocation(program, "uLut")
    uLutParams = GLES20.glGetUniformLocation(program, "uLutParams")
    uTone = GLES20.glGetUniformLocation(program, "uTone")
    uTone2 = GLES20.glGetUniformLocation(program, "uTone2")
    uTone3 = GLES20.glGetUniformLocation(program, "uTone3")
    uDetail = GLES20.glGetUniformLocation(program, "uDetail")
    uWb = GLES20.glGetUniformLocation(program, "uWb")
    uFrame = GLES20.glGetUniformLocation(program, "uFrame")
    uTexel = GLES20.glGetUniformLocation(program, "uTexel")
    uOverlay = GLES20.glGetUniformLocation(program, "uOverlay")
    uPeakColor = GLES20.glGetUniformLocation(program, "uPeakColor")
  }

  private fun compile(type: Int, source: String): Int {
    val shader = GLES20.glCreateShader(type)
    GLES20.glShaderSource(shader, source)
    GLES20.glCompileShader(shader)
    val status = IntArray(1)
    GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0)
    if (status[0] == 0) {
      val log = GLES20.glGetShaderInfoLog(shader)
      GLES20.glDeleteShader(shader)
      throw IllegalStateException("Grade shader compile failed: $log")
    }
    return shader
  }

  /**
   * Draws a full-viewport quad. The caller binds the target framebuffer/surface and sets the viewport.
   */
  fun draw(
    inputTexture: Int,
    texMatrix: FloatArray,
    posMatrix: FloatArray,
    grade: GradeUniforms,
    lutTexture: Int,
    frame: DrawFrame
  ) {
    GLES20.glUseProgram(program)
    GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0)
    GLES20.glDisable(GLES20.GL_BLEND)
    GLES20.glDisable(GLES20.GL_DEPTH_TEST)
    GLES20.glDisable(GLES20.GL_SCISSOR_TEST)
    GLES20.glDisable(GLES20.GL_CULL_FACE)

    quad.position(0)
    GLES20.glVertexAttribPointer(aPos, 2, GLES20.GL_FLOAT, false, 0, quad)
    GLES20.glEnableVertexAttribArray(aPos)

    GLES20.glUniformMatrix4fv(uTexMatrix, 1, false, texMatrix, 0)
    GLES20.glUniformMatrix4fv(uPosMatrix, 1, false, posMatrix, 0)

    GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
    GLES20.glBindTexture(if (external) GLES11Ext.GL_TEXTURE_EXTERNAL_OES else GLES20.GL_TEXTURE_2D, inputTexture)
    GLES20.glUniform1i(uTex, 0)
    GLES20.glActiveTexture(GLES20.GL_TEXTURE1)
    GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, lutTexture)
    GLES20.glUniform1i(uLut, 1)

    val bypass = frame.bypass
    GLES20.glUniform2f(uLutParams, grade.lutSize.toFloat(), if (lutTexture != 0) grade.lutMix else 0f)
    GLES20.glUniform4fv(uTone, 1, grade.tone, 0)
    GLES20.glUniform4fv(uTone2, 1, grade.tone2, 0)
    GLES20.glUniform4fv(uTone3, 1, grade.tone3, 0)
    GLES20.glUniform4f(uDetail, grade.detail[0], grade.detail[1], grade.detail[2], frame.detailScale)
    GLES20.glUniform3fv(uWb, 1, grade.wb, 0)
    GLES20.glUniform4f(uFrame, frame.outWidth.toFloat(), frame.outHeight.toFloat(), frame.sourceLongEdge, frame.seed)
    GLES20.glUniform2f(uTexel, frame.texelW, frame.texelH)
    GLES20.glUniform4f(
      uOverlay,
      if (frame.peaking) 1f else 0f,
      if (frame.zebra) 1f else 0f,
      if (bypass) 1f else 0f,
      0f
    )
    GLES20.glUniform3fv(uPeakColor, 1, frame.peakColor, 0)

    GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    GLES20.glDisableVertexAttribArray(aPos)
    GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
  }

  fun release() {
    GLES20.glDeleteProgram(program)
  }
}

/** Uploads a look LUT (N*N x N RGBA strip) and tracks which look is resident. */
class LutTexture {
  var texture: Int = 0
    private set
  var key: String? = null
    private set

  fun upload(key: String, size: Int, rgba: ByteBuffer) {
    if (texture == 0) texture = GlCore.create2dTexture()
    GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
    GLES20.glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 1)
    rgba.position(0)
    GLES20.glTexImage2D(
      GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, size * size, size, 0,
      GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, rgba
    )
    this.key = key
  }

  fun release() {
    GlCore.deleteTexture(texture)
    texture = 0
    key = null
  }
}
