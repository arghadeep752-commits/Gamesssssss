package com.cameroplus.engine.edit

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.graphics.SurfaceTexture
import android.net.Uri
import android.opengl.EGL14
import android.opengl.EGLSurface
import android.opengl.GLES20
import android.opengl.GLUtils
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.view.Surface
import android.view.TextureView
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.VideoSize
import androidx.media3.exoplayer.ExoPlayer
import com.cameroplus.engine.gl.Affine
import com.cameroplus.engine.gl.DrawFrame
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.gl.GlCore
import com.cameroplus.engine.gl.GradeProgram
import com.cameroplus.engine.gl.LutTexture
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.looks.GradeUniforms
import com.cameroplus.engine.looks.LutCache
import com.cameroplus.engine.media.MediaProbe
import expo.modules.kotlin.AppContext
import expo.modules.kotlin.viewevent.EventDispatcher
import expo.modules.kotlin.views.ExpoView
import java.util.concurrent.Executors
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Live edit preview for photos and videos. Renders with the same grading shader and geometry math
 * as the exporters, so what you see here is what gets saved.
 */
@SuppressLint("ViewConstructor")
@androidx.annotation.OptIn(androidx.media3.common.util.UnstableApi::class)
class CameroCanvasView(context: Context, appContext: AppContext) : ExpoView(context, appContext), TextureView.SurfaceTextureListener {
  override val shouldUseAndroidLayout: Boolean = true

  private val textureView = TextureView(context).apply {
    layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
    isOpaque = false
  }
  private val main = Handler(Looper.getMainLooper())
  private val glThread = HandlerThread("CameroCanvas").apply { start() }
  private val gl = Handler(glThread.looper)
  private val loader = Executors.newSingleThreadExecutor()

  // GL thread state
  private var core: GlCore? = null
  private var window: EGLSurface = EGL14.EGL_NO_SURFACE
  private var program2d: GradeProgram? = null
  private var programOes: GradeProgram? = null
  private val lut = LutTexture()
  private var viewW = 0
  private var viewH = 0
  private var imageTex = 0
  private var imageW = 0
  private var imageH = 0
  private var storedW = 0
  private var storedH = 0
  private var orientation = 1
  private var videoTex = 0
  private var videoST: SurfaceTexture? = null
  private var videoSurface: Surface? = null
  private var videoW = 0
  private var videoH = 0
  private val stMatrix = FloatArray(16)
  private var lastRect = IntArray(4)

  // Props (main thread), copied to the GL thread.
  private var source: String? = null
  private var kind: String = "image"
  @Volatile private var uniforms: GradeUniforms = GradeUniforms.NEUTRAL
  @Volatile private var transform: EditTransform = EditTransform()
  @Volatile private var compare = false
  @Volatile private var cropMode = false
  @Volatile private var insetPx = 0

  // Video playback (main thread)
  private var player: ExoPlayer? = null
  var playing = false
  var muted = false
  var speed = 1f
  var trimStartMs = 0L
  var trimEndMs = -1L
  private var lastSeek = -1L
  private var durationMs = 0L

  private val onCanvasLayout by EventDispatcher()
  private val onVideoInfo by EventDispatcher()
  private val onVideoProgress by EventDispatcher()
  private val onCanvasError by EventDispatcher()

  private val ticker = object : Runnable {
    override fun run() {
      val p = player ?: return
      val pos = p.currentPosition
      if (trimEndMs > 0 && pos >= trimEndMs) {
        p.seekTo(trimStartMs)
      } else if (pos < trimStartMs - 50) {
        p.seekTo(trimStartMs)
      }
      onVideoProgress(mapOf("positionMs" to pos.toDouble(), "durationMs" to durationMs.toDouble(), "playing" to p.isPlaying))
      main.postDelayed(this, 80)
    }
  }

  init {
    setBackgroundColor(Color.BLACK)
    textureView.surfaceTextureListener = this
    addView(textureView)
  }

  // ---- props ----

  var pendingSource: String? = null
  var pendingKind: String = "image"
  var pendingSeek: Long = -1L

  fun commitProps() {
    setSource(pendingSource, pendingKind)
    applyPlayback(pendingSeek)
  }

  fun setSource(uri: String?, type: String) {
    if (uri == source && type == kind) return
    source = uri
    kind = type
    releasePlayer()
    gl.post {
      GlCore.deleteTexture(imageTex)
      imageTex = 0
      imageW = 0
      imageH = 0
      releaseVideoTexture()
    }
    if (uri == null) return
    if (type == "video") {
      gl.post { setupVideoTexture() }
    } else {
      loadImage(uri)
    }
  }

  fun setGrade(json: String?) {
    uniforms = GradeParams.fromJson(json).uniforms()
    requestRender()
  }

  fun setTransform(json: String?) {
    transform = EditTransform.fromJson(json)
    requestRender()
  }

  fun setCompare(value: Boolean) {
    compare = value
    requestRender()
  }

  fun setCropMode(value: Boolean) {
    cropMode = value
    requestRender()
  }

  fun setInset(dp: Float) {
    insetPx = (dp * resources.displayMetrics.density).roundToInt()
    requestRender()
  }

  fun applyPlayback(seekMs: Long) {
    val p = player ?: return
    p.playWhenReady = playing
    p.volume = if (muted) 0f else 1f
    p.setPlaybackSpeed(speed.coerceIn(0.25f, 4f))
    if (seekMs >= 0 && seekMs != lastSeek) {
      lastSeek = seekMs
      p.seekTo(seekMs)
    }
  }

  private fun requestRender() {
    gl.post { render() }
  }

  // ---- image ----

  private fun loadImage(uri: String) {
    val target = max(max(width, height), 1080).coerceAtMost(2560)
    loader.execute {
      try {
        val parsed = MediaProbe.parse(uri)
        val bitmap = MediaProbe.decodeSampled(context, parsed, target) ?: throw IllegalStateException("Couldn't open this photo")
        val stored = MediaProbe.storedImageSize(context, parsed)
        val orient = MediaProbe.exifOrientation(context, parsed)
        gl.post {
          if (source != uri) {
            bitmap.recycle()
            return@post
          }
          val c = core
          if (c == null) {
            pendingBitmap?.recycle()
            pendingBitmap = bitmap
            pendingInfo = intArrayOf(stored[0], stored[1], orient)
            return@post
          }
          uploadImage(bitmap, stored, orient)
        }
      } catch (e: Exception) {
        main.post { onCanvasError(mapOf("message" to (e.message ?: "Couldn't open this photo"))) }
      }
    }
  }

  private var pendingBitmap: android.graphics.Bitmap? = null
  private var pendingInfo: IntArray? = null

  private fun uploadImage(bitmap: android.graphics.Bitmap, stored: IntArray, orient: Int) {
    core?.makeCurrentPbuffer()
    GlCore.deleteTexture(imageTex)
    imageTex = GlCore.create2dTexture()
    GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bitmap, 0)
    imageW = bitmap.width
    imageH = bitmap.height
    storedW = stored[0]
    storedH = stored[1]
    orientation = orient
    bitmap.recycle()
    render()
  }

  // ---- video ----

  private fun setupVideoTexture() {
    val c = core ?: return
    c.makeCurrentPbuffer()
    releaseVideoTexture()
    videoTex = GlCore.createOesTexture()
    val st = SurfaceTexture(videoTex)
    st.setOnFrameAvailableListener({ texture ->
      try {
        core?.makeCurrentPbuffer()
        texture.updateTexImage()
        texture.getTransformMatrix(stMatrix)
        render()
      } catch (_: Exception) {
      }
    }, gl)
    val surface = Surface(st)
    videoST = st
    videoSurface = surface
    val uri = source ?: return
    main.post { createPlayer(uri, surface) }
  }

  private fun releaseVideoTexture() {
    videoST?.setOnFrameAvailableListener(null)
    videoST?.release()
    videoST = null
    videoSurface?.release()
    videoSurface = null
    GlCore.deleteTexture(videoTex)
    videoTex = 0
  }

  private fun createPlayer(uri: String, surface: Surface) {
    releasePlayer()
    val p = ExoPlayer.Builder(context).build()
    p.repeatMode = Player.REPEAT_MODE_ALL
    p.setVideoSurface(surface)
    p.addListener(object : Player.Listener {
      override fun onVideoSizeChanged(videoSize: VideoSize) {
        val w = (videoSize.width * videoSize.pixelWidthHeightRatio).roundToInt()
        val h = videoSize.height
        gl.post {
          videoW = w
          videoH = h
          render()
        }
      }

      override fun onPlaybackStateChanged(playbackState: Int) {
        if (playbackState == Player.STATE_READY) {
          durationMs = max(0L, p.duration)
          onVideoInfo(mapOf("durationMs" to durationMs.toDouble(), "width" to videoW, "height" to videoH))
        }
      }

      override fun onPlayerError(error: PlaybackException) {
        onCanvasError(mapOf("message" to (error.message ?: "This video can't be played")))
      }
    })
    p.setMediaItem(MediaItem.fromUri(MediaProbe.parse(uri)))
    p.prepare()
    player = p
    applyPlayback(-1)
    main.removeCallbacks(ticker)
    main.post(ticker)
  }

  private fun releasePlayer() {
    main.removeCallbacks(ticker)
    player?.release()
    player = null
    lastSeek = -1
  }

  // ---- rendering (GL thread) ----

  private fun render() {
    val c = core ?: return
    if (window == EGL14.EGL_NO_SURFACE || viewW <= 0 || viewH <= 0) return
    if (!c.makeCurrent(window)) return
    GLES20.glViewport(0, 0, viewW, viewH)
    GLES20.glClearColor(0f, 0f, 0f, 1f)
    GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)

    val isVideo = kind == "video"
    val dw: Int
    val dh: Int
    if (isVideo) {
      if (videoTex == 0 || videoW <= 0) { c.swap(window); return }
      dw = videoW; dh = videoH
    } else {
      if (imageTex == 0) { c.swap(window); return }
      val swap = Affine.exifSwapsAxes(orientation)
      dw = if (swap) imageH else imageW
      dh = if (swap) imageW else imageH
    }
    val t = transform
    val out = t.outputSize(dw, dh, ignoreCrop = cropMode)
    val availW = viewW - 2 * insetPx
    val availH = viewH - 2 * insetPx
    val scale = min(availW.toFloat() / out[0], availH.toFloat() / out[1])
    val rw = max(1, (out[0] * scale).roundToInt())
    val rh = max(1, (out[1] * scale).roundToInt())
    val rx = (viewW - rw) / 2
    val ryTop = (viewH - rh) / 2
    GLES20.glViewport(rx, viewH - ryTop - rh, rw, rh)

    val geometry = t.outputToDisplayed(ignoreCrop = cropMode) * Affine.FLIP_Y
    val texMatrix = if (isVideo) {
      (Affine.fromMat4(stMatrix) * Affine.FLIP_Y * geometry).toMat4()
    } else {
      (Affine.exifDisplayedToStored(orientation) * geometry).toMat4()
    }
    val program = if (isVideo) {
      programOes ?: GradeProgram(external = true).also { programOes = it }
    } else {
      program2d ?: GradeProgram(external = false).also { program2d = it }
    }
    val grade = uniforms
    val key = grade.lutKey
    if (key != null && lut.key != key) {
      LutCache.get(key)?.let { lut.upload(key, grade.lutSize, it) }
    }
    val lutTex = if (key != null && lut.key == key) lut.texture else 0
    val texW = if (isVideo) videoW else imageW
    val texH = if (isVideo) videoH else imageH
    val detailScale = if (!isVideo && storedW > 0) imageW.toFloat() / storedW else 1f
    val longEdge = if (isVideo) max(videoW, videoH).toFloat() else max(storedW, storedH).toFloat()
    program.draw(
      if (isVideo) videoTex else imageTex,
      texMatrix,
      Affine.FLIP_Y.toMat4(),
      grade,
      lutTex,
      DrawFrame(rw, rh, 1f / max(texW, 1), 1f / max(texH, 1), longEdge, detailScale, bypass = compare)
    )
    c.swap(window)

    if (rx != lastRect[0] || ryTop != lastRect[1] || rw != lastRect[2] || rh != lastRect[3]) {
      lastRect = intArrayOf(rx, ryTop, rw, rh)
      val density = resources.displayMetrics.density
      main.post {
        onCanvasLayout(
          mapOf(
            "x" to (rx / density).toDouble(),
            "y" to (ryTop / density).toDouble(),
            "width" to (rw / density).toDouble(),
            "height" to (rh / density).toDouble(),
            "sourceWidth" to dw,
            "sourceHeight" to dh
          )
        )
      }
    }
  }

  // ---- TextureView ----

  override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) {
    gl.post {
      try {
        val c = core ?: GlCore(recordable = false).also { core = it }
        window = c.createWindowSurface(surface)
        viewW = width
        viewH = height
        pendingBitmap?.let { bmp ->
          val info = pendingInfo ?: intArrayOf(bmp.width, bmp.height, 1)
          pendingBitmap = null
          uploadImage(bmp, intArrayOf(info[0], info[1]), info[2])
        }
        if (kind == "video" && source != null && videoTex == 0) setupVideoTexture()
        render()
      } catch (e: Exception) {
        main.post { onCanvasError(mapOf("message" to "GPU preview unavailable: ${e.message}")) }
      }
    }
  }

  override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) {
    gl.post {
      viewW = width
      viewH = height
      render()
    }
  }

  override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean {
    val latch = java.util.concurrent.CountDownLatch(1)
    gl.post {
      core?.destroySurface(window)
      window = EGL14.EGL_NO_SURFACE
      core?.makeCurrentPbuffer()
      latch.countDown()
    }
    latch.await(500, java.util.concurrent.TimeUnit.MILLISECONDS)
    return true
  }

  override fun onSurfaceTextureUpdated(surface: SurfaceTexture) = Unit

  fun destroy() {
    releasePlayer()
    gl.post {
      releaseVideoTexture()
      GlCore.deleteTexture(imageTex)
      imageTex = 0
      lut.release()
      program2d?.release()
      programOes?.release()
      program2d = null
      programOes = null
      core?.destroySurface(window)
      window = EGL14.EGL_NO_SURFACE
      core?.release()
      core = null
      pendingBitmap?.recycle()
      pendingBitmap = null
    }
    gl.postDelayed({ glThread.quitSafely() }, 500)
    loader.shutdown()
  }

  @Suppress("unused")
  private fun uriOf(s: String): Uri = MediaProbe.parse(s)
}
