package com.cameroplus.engine.camera

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import androidx.camera.view.PreviewView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import com.cameroplus.engine.looks.GradeParams
import expo.modules.kotlin.AppContext
import expo.modules.kotlin.viewevent.EventDispatcher
import expo.modules.kotlin.views.ExpoView
import org.json.JSONObject
import java.lang.ref.WeakReference

/** Lifecycle owned by the camera view: resumed only while the view is attached, active and in the foreground. */
class ViewLifecycleOwner : LifecycleOwner {
  private val registry = LifecycleRegistry(this)
  override val lifecycle: Lifecycle get() = registry

  fun moveTo(state: Lifecycle.State) {
    if (registry.currentState == Lifecycle.State.DESTROYED) return
    if (registry.currentState != state) registry.currentState = state
  }
}

internal fun cleanMap(map: Map<String, Any?>): Map<String, Any> {
  val out = HashMap<String, Any>()
  for ((k, v) in map) if (v != null) out[k] = v
  return out
}

@SuppressLint("ViewConstructor")
class CameroCameraView(context: Context, appContext: AppContext) : ExpoView(context, appContext), CameraListener {
  override val shouldUseAndroidLayout: Boolean = true

  private val previewView = PreviewView(context).apply {
    layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
    implementationMode = PreviewView.ImplementationMode.COMPATIBLE
    scaleType = PreviewView.ScaleType.FIT_CENTER
    setBackgroundColor(Color.BLACK)
  }

  private val owner = ViewLifecycleOwner()
  var session: CameraSession? = null
    private set

  var active = true
  var cameraId: String? = null
  var mode = "photo"
  var aspect = "4:3"
  var photoJson: String? = null
  var videoJson: String? = null
  var gradeJson: String? = null
  var overlayJson: String? = null
  var flash = "off"
  var torch = false
  var manualJson: String? = null
  var timelapseIntervalMs = 1000

  private var attached = false
  private var hostResumed = true
  private var hostLifecycle: Lifecycle? = null
  private val hostObserver = LifecycleEventObserver { _, event ->
    when (event) {
      Lifecycle.Event.ON_RESUME -> { hostResumed = true; updateLifecycle() }
      Lifecycle.Event.ON_PAUSE -> { hostResumed = false; updateLifecycle() }
      else -> Unit
    }
  }

  private val onReady by EventDispatcher()
  private val onZoomChanged by EventDispatcher()
  private val onFocusResult by EventDispatcher()
  private val onRecordingEvent by EventDispatcher()
  private val onPhotoEvent by EventDispatcher()
  private val onCameraMetadata by EventDispatcher()
  private val onOrientationChanged by EventDispatcher()
  private val onPreviewState by EventDispatcher()
  private val onCameraError by EventDispatcher()

  init {
    setBackgroundColor(Color.BLACK)
    addView(previewView)
    owner.moveTo(Lifecycle.State.CREATED)
  }

  override fun onAttachedToWindow() {
    super.onAttachedToWindow()
    attached = true
    current = WeakReference(this)
    val activity = appContext.currentActivity
    if (activity is LifecycleOwner && hostLifecycle == null) {
      hostLifecycle = activity.lifecycle.also {
        it.addObserver(hostObserver)
        hostResumed = it.currentState.isAtLeast(Lifecycle.State.RESUMED)
      }
    }
    ensureSession()
    updateLifecycle()
  }

  override fun onDetachedFromWindow() {
    attached = false
    updateLifecycle()
    if (current?.get() === this) current = null
    super.onDetachedFromWindow()
  }

  private fun ensureSession() {
    if (session == null) session = CameraSession(context, previewView, owner, this)
  }

  private fun updateLifecycle() {
    val state = if (attached && active && hostResumed) Lifecycle.State.RESUMED else Lifecycle.State.CREATED
    owner.moveTo(state)
  }

  fun applyProps() {
    ensureSession()
    val s = session ?: return
    if (active) current = WeakReference(this)
    s.setGrade(GradeParams.fromJson(gradeJson))
    s.setOverlay(parseOverlay(overlayJson))
    s.setFlash(flash)
    s.setManual(ManualConfig.fromJson(manualJson))
    s.update(
      SessionConfigState(
        cameraId = cameraId,
        mode = mode,
        aspect = aspect,
        photo = PhotoConfig.fromJson(photoJson),
        video = VideoConfig.fromJson(videoJson),
        timelapseIntervalMs = timelapseIntervalMs
      )
    )
    s.setTorch(torch)
    updateLifecycle()
  }

  private fun parseOverlay(json: String?): OverlayState {
    if (json.isNullOrBlank()) return OverlayState()
    return try {
      val o = JSONObject(json)
      val color = o.optString("peakColor", "#FFB46B")
      OverlayState(
        peaking = o.optBoolean("peaking", false),
        zebra = o.optBoolean("zebra", false),
        bypass = o.optBoolean("bypass", false),
        peakColor = parseColor(color)
      )
    } catch (e: Exception) {
      OverlayState()
    }
  }

  private fun parseColor(hex: String): FloatArray = try {
    val c = Color.parseColor(hex)
    floatArrayOf(Color.red(c) / 255f, Color.green(c) / 255f, Color.blue(c) / 255f)
  } catch (e: Exception) {
    floatArrayOf(1f, 0.706f, 0.42f)
  }

  fun dpToPx(dp: Float): Float = dp * resources.displayMetrics.density

  fun destroy() {
    hostLifecycle?.removeObserver(hostObserver)
    hostLifecycle = null
    session?.destroy()
    session = null
    owner.moveTo(Lifecycle.State.DESTROYED)
    if (current?.get() === this) current = null
  }

  // CameraListener
  override fun emitReady(info: Map<String, Any?>) = onReady(cleanMap(info))
  override fun emitZoom(ratio: Float) = onZoomChanged(mapOf("ratio" to ratio.toDouble()))
  override fun emitFocus(result: Map<String, Any?>) = onFocusResult(cleanMap(result))
  override fun emitRecording(event: Map<String, Any?>) = onRecordingEvent(cleanMap(event))
  override fun emitPhoto(event: Map<String, Any?>) = onPhotoEvent(cleanMap(event))
  override fun emitMetadata(values: Map<String, Any?>) = onCameraMetadata(cleanMap(values))
  override fun emitOrientation(degrees: Int) = onOrientationChanged(mapOf("degrees" to degrees))
  override fun emitPreviewState(streaming: Boolean) = onPreviewState(mapOf("streaming" to streaming))
  override fun emitError(code: String, message: String) = onCameraError(mapOf("code" to code, "message" to message))

  companion object {
    @Volatile
    var current: WeakReference<CameroCameraView>? = null
  }
}
