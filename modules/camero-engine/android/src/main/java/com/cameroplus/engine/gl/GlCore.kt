package com.cameroplus.engine.gl

import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLDisplay
import android.opengl.EGLExt
import android.opengl.EGLSurface
import android.opengl.GLES20

/**
 * Minimal EGL wrapper. One instance owns one GLES 2 context bound to the thread that created it.
 * The config is "recordable" so the same context can render into MediaCodec input surfaces.
 */
class GlCore(recordable: Boolean = true) {
  val display: EGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
  val config: EGLConfig
  val context: EGLContext
  private var pbuffer: EGLSurface = EGL14.EGL_NO_SURFACE

  init {
    check(display != EGL14.EGL_NO_DISPLAY) { "EGL display unavailable" }
    val version = IntArray(2)
    check(EGL14.eglInitialize(display, version, 0, version, 1)) { "eglInitialize failed" }
    config = chooseConfig(recordable) ?: chooseConfig(false) ?: error("No suitable EGL config")
    context = EGL14.eglCreateContext(
      display, config, EGL14.EGL_NO_CONTEXT,
      intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0
    )
    check(context != EGL14.EGL_NO_CONTEXT) { "eglCreateContext failed: 0x${Integer.toHexString(EGL14.eglGetError())}" }
    pbuffer = EGL14.eglCreatePbufferSurface(
      display, config, intArrayOf(EGL14.EGL_WIDTH, 1, EGL14.EGL_HEIGHT, 1, EGL14.EGL_NONE), 0
    )
    makeCurrentPbuffer()
  }

  private fun chooseConfig(recordable: Boolean): EGLConfig? {
    val attribs = mutableListOf(
      EGL14.EGL_RED_SIZE, 8,
      EGL14.EGL_GREEN_SIZE, 8,
      EGL14.EGL_BLUE_SIZE, 8,
      EGL14.EGL_ALPHA_SIZE, 8,
      EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
      EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT or EGL14.EGL_PBUFFER_BIT
    )
    if (recordable) {
      attribs.add(EGLExt.EGL_RECORDABLE_ANDROID)
      attribs.add(1)
    }
    attribs.add(EGL14.EGL_NONE)
    val configs = arrayOfNulls<EGLConfig>(1)
    val count = IntArray(1)
    val ok = EGL14.eglChooseConfig(display, attribs.toIntArray(), 0, configs, 0, 1, count, 0)
    return if (ok && count[0] > 0) configs[0] else null
  }

  fun createWindowSurface(nativeWindow: Any): EGLSurface {
    val surface = EGL14.eglCreateWindowSurface(display, config, nativeWindow, intArrayOf(EGL14.EGL_NONE), 0)
    check(surface != EGL14.EGL_NO_SURFACE) { "eglCreateWindowSurface failed: 0x${Integer.toHexString(EGL14.eglGetError())}" }
    return surface
  }

  fun makeCurrent(surface: EGLSurface): Boolean = EGL14.eglMakeCurrent(display, surface, surface, context)

  fun makeCurrentPbuffer(): Boolean = makeCurrent(pbuffer)

  fun swap(surface: EGLSurface): Boolean = EGL14.eglSwapBuffers(display, surface)

  fun setPresentationTime(surface: EGLSurface, nanos: Long) {
    EGLExt.eglPresentationTimeANDROID(display, surface, nanos)
  }

  fun destroySurface(surface: EGLSurface) {
    if (surface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, surface)
  }

  fun surfaceSize(surface: EGLSurface): IntArray {
    val w = IntArray(1)
    val h = IntArray(1)
    EGL14.eglQuerySurface(display, surface, EGL14.EGL_WIDTH, w, 0)
    EGL14.eglQuerySurface(display, surface, EGL14.EGL_HEIGHT, h, 0)
    return intArrayOf(w[0], h[0])
  }

  /** Releases the context. The default display is shared process-wide, so it is not terminated. */
  fun release() {
    EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
    destroySurface(pbuffer)
    pbuffer = EGL14.EGL_NO_SURFACE
    EGL14.eglDestroyContext(display, context)
    EGL14.eglReleaseThread()
  }

  companion object {
    fun maxTextureSize(): Int {
      val v = IntArray(1)
      GLES20.glGetIntegerv(GLES20.GL_MAX_TEXTURE_SIZE, v, 0)
      return if (v[0] > 0) v[0] else 2048
    }

    fun createOesTexture(): Int {
      val ids = IntArray(1)
      GLES20.glGenTextures(1, ids, 0)
      GLES20.glBindTexture(android.opengl.GLES11Ext.GL_TEXTURE_EXTERNAL_OES, ids[0])
      GLES20.glTexParameteri(android.opengl.GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
      GLES20.glTexParameteri(android.opengl.GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
      GLES20.glTexParameteri(android.opengl.GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
      GLES20.glTexParameteri(android.opengl.GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
      return ids[0]
    }

    fun create2dTexture(): Int {
      val ids = IntArray(1)
      GLES20.glGenTextures(1, ids, 0)
      GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, ids[0])
      GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
      GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
      GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
      GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
      return ids[0]
    }

    fun deleteTexture(id: Int) {
      if (id != 0) GLES20.glDeleteTextures(1, intArrayOf(id), 0)
    }
  }
}
