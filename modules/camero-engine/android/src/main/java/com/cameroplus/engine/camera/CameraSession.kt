package com.cameroplus.engine.camera

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.TotalCaptureResult
import android.media.MediaActionSound
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.util.Range
import android.util.Rational
import android.util.Size
import android.view.OrientationEventListener
import android.view.Surface
import androidx.annotation.OptIn
import androidx.camera.camera2.interop.Camera2CameraControl
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.camera2.interop.CaptureRequestOptions
import androidx.camera.camera2.interop.ExperimentalCamera2Interop
import androidx.camera.core.Camera
import androidx.camera.core.CameraEffect
import androidx.camera.core.CameraInfo
import androidx.camera.core.CameraSelector
import androidx.camera.core.CameraState
import androidx.camera.core.DynamicRange
import androidx.camera.core.ExperimentalSessionConfig
import androidx.camera.video.ExperimentalHighSpeedVideo
import androidx.camera.core.FocusMeteringAction
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.core.UseCaseGroup
import androidx.camera.core.ViewPort
import androidx.camera.core.ZoomState
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.extensions.ExtensionMode
import androidx.camera.extensions.ExtensionsManager
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FallbackStrategy
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.HighSpeedVideoSessionConfig
import androidx.camera.video.MediaStoreOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.core.util.Consumer
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.Observer
import com.cameroplus.engine.edit.PhotoRenderer
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.media.MediaProbe
import com.cameroplus.engine.media.MediaStoreWriter
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Effect wrapper that hands camera frames to the grading processor. */
class GradeEffect(targets: Int, processor: GradeSurfaceProcessor, onError: Consumer<Throwable>) :
  CameraEffect(targets, processor.executor, processor, onError)

interface CameraListener {
  fun emitReady(info: Map<String, Any?>)
  fun emitZoom(ratio: Float)
  fun emitFocus(result: Map<String, Any?>)
  fun emitRecording(event: Map<String, Any?>)
  fun emitPhoto(event: Map<String, Any?>)
  fun emitMetadata(values: Map<String, Any?>)
  fun emitOrientation(degrees: Int)
  fun emitPreviewState(streaming: Boolean)
  fun emitError(code: String, message: String)
}

@OptIn(ExperimentalCamera2Interop::class)
class CameraSession(
  private val context: Context,
  private val previewView: PreviewView,
  private val lifecycleOwner: LifecycleOwner,
  private val listener: CameraListener
) {
  private val main = Handler(Looper.getMainLooper())
  private val mainExecutor = ContextCompat.getMainExecutor(context)
  private val io = Executors.newSingleThreadExecutor()
  private val processing = Executors.newSingleThreadExecutor()
  private val captureDir = File(context.cacheDir, "capture").apply { mkdirs() }

  private var provider: ProcessCameraProvider? = null
  private var extensions: ExtensionsManager? = null
  private var extensionsReady = false
  private var camera: Camera? = null
  private var imageCapture: ImageCapture? = null
  private var videoCapture: VideoCapture<Recorder>? = null
  private var recording: Recording? = null
  private var processor: GradeSurfaceProcessor? = null
  private var effectActive = false
  private var effectTargets = 0
  private var activeExtension = "none"

  private var config = SessionConfigState()
  private var boundKey: String? = null
  private var pendingRebind = false
  private var grade = GradeParams.NEUTRAL
  private var manual = ManualConfig()
  private var flashMode = "off"
  private var torch = false
  private var requestedZoom = 1f
  private var focusLocked = false
  private var targetRotation = Surface.ROTATION_0
  private var destroyed = false

  private var observedInfo: CameraInfo? = null
  private val zoomObserver = Observer<ZoomState> { listener.emitZoom(it.zoomRatio) }
  private val stateObserver = Observer<CameraState> { state -> handleCameraState(state) }
  private val streamObserver = Observer<PreviewView.StreamState> { listener.emitPreviewState(it == PreviewView.StreamState.STREAMING) }

  @Volatile private var wantMetadata = false
  @Volatile private var lastMetaAt = 0L
  @Volatile private var lastIso = 100
  @Volatile private var lastExposureNs = 16_666_666L

  private var timelapseActive = false
  private var timelapseStartedAt = 0L
  private val timelapseTicker = object : Runnable {
    override fun run() {
      if (!timelapseActive) return
      val frames = processor?.timelapse?.frameCount ?: 0
      listener.emitRecording(
        mapOf(
          "state" to "recording",
          "durationMs" to (SystemClock.elapsedRealtime() - timelapseStartedAt),
          "frames" to frames,
          "clipMs" to frames * 1000L / TimelapseEncoder.FPS
        )
      )
      main.postDelayed(this, 500)
    }
  }

  private val shutterSound = MediaActionSound().apply {
    try { load(MediaActionSound.SHUTTER_CLICK) } catch (_: Exception) {}
  }

  private val orientationListener = object : OrientationEventListener(context) {
    private var current = -1
    override fun onOrientationChanged(degrees: Int) {
      if (degrees == ORIENTATION_UNKNOWN) return
      val next = when {
        current == -1 -> nearest(degrees)
        abs(angleDiff(degrees, current)) < 55 -> current
        else -> nearest(degrees)
      }
      if (next == current) return
      current = next
      targetRotation = when (next) {
        90 -> Surface.ROTATION_270
        180 -> Surface.ROTATION_180
        270 -> Surface.ROTATION_90
        else -> Surface.ROTATION_0
      }
      imageCapture?.targetRotation = targetRotation
      if (recording == null) videoCapture?.targetRotation = targetRotation
      val ui = when (next) { 90 -> -90; 180 -> 180; 270 -> 90; else -> 0 }
      listener.emitOrientation(ui)
    }

    private fun nearest(d: Int): Int = (((d + 45) / 90) * 90) % 360
    private fun angleDiff(a: Int, b: Int): Int {
      var x = (a - b) % 360
      if (x > 180) x -= 360
      if (x < -180) x += 360
      return x
    }
    private fun abs(v: Int) = if (v < 0) -v else v
  }

  init {
    processor = GradeSurfaceProcessor { message -> main.post { listener.emitError("gpu", message) } }
    previewView.previewStreamState.observe(lifecycleOwner, streamObserver)
    if (orientationListener.canDetectOrientation()) orientationListener.enable()
    val future = ProcessCameraProvider.getInstance(context)
    future.addListener({
      if (destroyed) return@addListener
      try {
        val p = future.get()
        provider = p
        rebind()
        val ext = ExtensionsManager.getInstanceAsync(context, p)
        ext.addListener({
          if (destroyed) return@addListener
          extensions = try { ext.get() } catch (e: Exception) { null }
          extensionsReady = true
          if (needsExtension(config) && boundKey != config.bindKey(true)) rebind()
        }, mainExecutor)
      } catch (e: Exception) {
        listener.emitError("provider", "Camera service unavailable: ${e.message}")
      }
    }, mainExecutor)
  }

  // ---- configuration ----

  fun update(next: SessionConfigState) {
    config = next
    wantMetadata = next.mode == "pro" || next.mode == "macro"
    if (provider == null) return
    if (recording != null || timelapseActive) {
      pendingRebind = boundKey != next.bindKey(extensionsReady)
      return
    }
    if (boundKey != next.bindKey(extensionsReady)) rebind() else applyCaptureOptions()
  }

  fun setGrade(params: GradeParams) {
    grade = params
    processor?.setGrade(params)
  }

  fun setOverlay(state: OverlayState) {
    processor?.overlay = state
  }

  fun setFlash(mode: String) {
    flashMode = mode
    imageCapture?.flashMode = flashInt(mode)
  }

  fun setTorch(on: Boolean) {
    torch = on
    val cam = camera ?: return
    if (cam.cameraInfo.hasFlashUnit()) cam.cameraControl.enableTorch(on)
  }

  fun setManual(next: ManualConfig) {
    val keepLock = focusLocked && manual.aeLock
    val merged = if (keepLock) next.copy(aeLock = true) else next
    if (merged == manual) return
    manual = merged
    applyCaptureOptions()
  }

  private fun flashInt(mode: String) = when (mode) {
    "on" -> ImageCapture.FLASH_MODE_ON
    "auto" -> ImageCapture.FLASH_MODE_AUTO
    else -> ImageCapture.FLASH_MODE_OFF
  }

  private fun needsExtension(cfg: SessionConfigState) =
    cfg.mode == "portrait" || (cfg.mode == "photo" && cfg.photo.extension != "none")

  private fun extensionFor(cfg: SessionConfigState): Int = when {
    cfg.mode == "portrait" -> ExtensionMode.BOKEH
    cfg.mode != "photo" -> ExtensionMode.NONE
    cfg.photo.extension == "hdr" -> ExtensionMode.HDR
    cfg.photo.extension == "night" -> ExtensionMode.NIGHT
    cfg.photo.extension == "auto" -> ExtensionMode.AUTO
    else -> ExtensionMode.NONE
  }

  private fun aspectRational(cfg: SessionConfigState): Rational = when {
    cfg.isVideoMode || cfg.aspect == "16:9" -> Rational(9, 16)
    cfg.aspect == "1:1" -> Rational(1, 1)
    else -> Rational(3, 4)
  }

  private fun aspectStrategy(cfg: SessionConfigState): AspectRatioStrategy =
    if (cfg.isVideoMode || cfg.aspect == "16:9") AspectRatioStrategy.RATIO_16_9_FALLBACK_AUTO_STRATEGY
    else AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY

  private fun lowTier(): Boolean {
    val am = context.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
    val mem = android.app.ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
    return am.isLowRamDevice || mem.totalMem < 3_500L * 1024 * 1024
  }

  private fun previewSelector(cfg: SessionConfigState): ResolutionSelector {
    val wide = cfg.isVideoMode || cfg.aspect == "16:9"
    val bound = when {
      lowTier() -> if (wide) Size(1280, 720) else Size(1280, 960)
      else -> if (wide) Size(1920, 1080) else Size(1440, 1080)
    }
    return ResolutionSelector.Builder()
      .setAspectRatioStrategy(aspectStrategy(cfg))
      .setResolutionStrategy(ResolutionStrategy(bound, ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER))
      .build()
  }

  private fun photoSelector(cfg: SessionConfigState): ResolutionSelector {
    val b = ResolutionSelector.Builder().setAspectRatioStrategy(aspectStrategy(cfg))
    when (cfg.photo.resolution) {
      "standard" -> b.setResolutionStrategy(
        ResolutionStrategy(
          if (cfg.aspect == "16:9") Size(3840, 2160) else Size(3264, 2448),
          ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER
        )
      )
      "highres" -> {
        b.setResolutionStrategy(ResolutionStrategy.HIGHEST_AVAILABLE_STRATEGY)
        b.setAllowedResolutionMode(ResolutionSelector.PREFER_HIGHER_RESOLUTION_OVER_CAPTURE_RATE)
      }
      else -> b.setResolutionStrategy(ResolutionStrategy.HIGHEST_AVAILABLE_STRATEGY)
    }
    return b.build()
  }

  private fun bitrateFor(quality: Quality, fps: Int, level: String): Int? {
    if (level == "auto") return null
    val base = when (quality) {
      Quality.UHD -> if (level == "max") 80_000_000 else 50_000_000
      Quality.FHD -> if (level == "max") 30_000_000 else 20_000_000
      Quality.HD -> if (level == "max") 14_000_000 else 10_000_000
      else -> if (level == "max") 8_000_000 else 5_000_000
    }
    return (base.toLong() * maxOf(fps, 24) / 30).toInt()
  }

  // ---- binding ----

  private data class Attempt(val effect: Boolean, val fps: Boolean, val stabilization: Boolean)

  private fun rebind() {
    val p = provider ?: return
    if (destroyed) return
    val cfg = config
    val infos = p.availableCameraInfos
    if (infos.isEmpty()) {
      listener.emitError("no_camera", "This device reports no cameras.")
      return
    }
    val info = infos.firstOrNull { CameraCatalog.cameraId(it) == cfg.cameraId }
      ?: infos.firstOrNull { it.lensFacing == CameraSelector.LENS_FACING_BACK }
      ?: infos.first()

    var selector = info.cameraSelector
    activeExtension = "none"
    val extMode = extensionFor(cfg)
    val em = extensions
    if (extMode != ExtensionMode.NONE && em != null) {
      try {
        if (em.isExtensionAvailable(selector, extMode)) {
          selector = em.getExtensionEnabledCameraSelector(selector, extMode)
          activeExtension = when (extMode) {
            ExtensionMode.BOKEH -> "bokeh"
            ExtensionMode.HDR -> "hdr"
            ExtensionMode.NIGHT -> "night"
            ExtensionMode.AUTO -> "auto"
            else -> "none"
          }
        }
      } catch (e: Exception) {
        Log.w(TAG, "Extension unavailable", e)
      }
    }

    detachObservers()
    p.unbindAll()
    camera = null
    imageCapture = null
    videoCapture = null
    effectActive = false

    val attempts = listOf(Attempt(true, true, true), Attempt(true, false, false), Attempt(false, false, false))
    var lastError: Throwable? = null
    val notes = ArrayList<String>()
    for ((index, attempt) in attempts.withIndex()) {
      try {
        bindAttempt(p, info, selector, cfg, attempt)
        if (index > 0) {
          if (!attempt.fps && cfg.isVideoMode) notes.add("fps")
          if (!attempt.effect) notes.add("look")
        }
        break
      } catch (e: Throwable) {
        Log.w(TAG, "Bind attempt $index failed", e)
        lastError = e
        try { p.unbindAll() } catch (_: Exception) {}
        camera = null
      }
    }
    val cam = camera
    if (cam == null) {
      boundKey = null
      listener.emitError("bind_failed", lastError?.message ?: "The camera could not start.")
      return
    }
    boundKey = cfg.bindKey(extensionsReady)
    attachObservers(cam.cameraInfo)
    imageCapture?.flashMode = flashInt(flashMode)
    if (torch && cam.cameraInfo.hasFlashUnit()) cam.cameraControl.enableTorch(true)
    val zs = cam.cameraInfo.zoomState.value
    if (zs != null) {
      val z = requestedZoom.coerceIn(zs.minZoomRatio, zs.maxZoomRatio)
      if (z != 1f) cam.cameraControl.setZoomRatio(z)
    }
    focusLocked = false
    processor?.setGrade(grade)
    applyCaptureOptions()
    listener.emitReady(readyInfo(cam, cfg, notes))
  }

  @kotlin.OptIn(ExperimentalSessionConfig::class, ExperimentalHighSpeedVideo::class)
  private fun bindAttempt(p: ProcessCameraProvider, info: CameraInfo, selector: CameraSelector, cfg: SessionConfigState, attempt: Attempt) {
    val rotation = previewView.display?.rotation ?: Surface.ROTATION_0
    val viewPort = ViewPort.Builder(aspectRational(cfg), rotation).setScaleType(ViewPort.FILL_CENTER).build()

    val previewBuilder = Preview.Builder().setResolutionSelector(previewSelector(cfg))
    Camera2Interop.Extender(previewBuilder).setSessionCaptureCallback(captureCallback)

    if (cfg.mode == "slowmo") {
      val hs = Recorder.getHighSpeedVideoCapabilities(info) ?: throw IllegalStateException("Slow motion isn't supported by this camera")
      val q = hs.getSupportedQualities(DynamicRange.SDR).firstOrNull() ?: throw IllegalStateException("No slow-motion quality available")
      val recorder = Recorder.Builder().setQualitySelector(QualitySelector.from(q)).build()
      val vc = VideoCapture.withOutput(recorder)
      val preview = Preview.Builder().build()
      preview.setSurfaceProvider(previewView.surfaceProvider)
      val probe = HighSpeedVideoSessionConfig(vc, preview)
      val ranges = info.getSupportedFrameRateRanges(probe)
      val range = ranges.filter { it.upper == cfg.video.slowFps }.maxByOrNull { it.lower }
        ?: ranges.maxByOrNull { it.upper } ?: throw IllegalStateException("No high-speed frame rate available")
      val session = HighSpeedVideoSessionConfig(vc, preview, range, true)
      processor?.setStabilization(false)
      camera = p.bindToLifecycle(lifecycleOwner, selector, session)
      videoCapture = vc
      effectActive = false
      effectTargets = 0
      return
    }

    val videoMode = cfg.mode == "video" || cfg.mode == "timelapse"
    val fps = cfg.video.fps
    if (cfg.mode == "video" && attempt.fps) previewBuilder.setTargetFrameRate(Range(fps, fps))
    val wantEnhanced = cfg.mode == "video" && attempt.stabilization && cfg.video.stabilization == "enhanced"
    if (wantEnhanced && !cfg.video.hdr && Preview.getPreviewCapabilities(info).isStabilizationSupported &&
      !Recorder.getVideoCapabilities(info).isStabilizationSupported
    ) {
      previewBuilder.setPreviewStabilizationEnabled(true)
    }
    val preview = previewBuilder.build()
    preview.setSurfaceProvider(previewView.surfaceProvider)

    var ic: ImageCapture? = null
    var vc: VideoCapture<Recorder>? = null
    if (!videoMode) {
      val b = ImageCapture.Builder()
        .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
        .setJpegQuality(cfg.photo.jpegQuality)
        .setFlashMode(flashInt(flashMode))
        .setTargetRotation(targetRotation)
        .setResolutionSelector(photoSelector(cfg))
      val formats = try {
        ImageCapture.getImageCaptureCapabilities(p.getCameraInfo(selector)).supportedOutputFormats
      } catch (e: Exception) {
        emptySet<Int>()
      }
      if (cfg.photo.format == "raw+jpeg" && formats.contains(ImageCapture.OUTPUT_FORMAT_RAW_JPEG)) {
        b.setOutputFormat(ImageCapture.OUTPUT_FORMAT_RAW_JPEG)
      } else if (cfg.photo.format == "ultrahdr" && formats.contains(ImageCapture.OUTPUT_FORMAT_JPEG_ULTRA_HDR)) {
        b.setOutputFormat(ImageCapture.OUTPUT_FORMAT_JPEG_ULTRA_HDR)
      }
      ic = b.build()
    } else if (cfg.mode == "video") {
      val quality = CameraCatalog.qualityFromName(cfg.video.quality)
      val rb = Recorder.Builder()
        .setQualitySelector(QualitySelector.from(quality, FallbackStrategy.lowerQualityOrHigherThan(quality)))
      bitrateFor(quality, fps, cfg.video.bitrate)?.let { rb.setTargetVideoEncodingBitRate(it) }
      val vb = VideoCapture.Builder(rb.build()).setTargetRotation(targetRotation)
      if (attempt.fps) vb.setTargetFrameRate(Range(fps, fps))
      if (wantEnhanced && Recorder.getVideoCapabilities(info).isStabilizationSupported) vb.setVideoStabilizationEnabled(true)
      if (cfg.video.hdr && Recorder.getVideoCapabilities(info).supportedDynamicRanges.contains(DynamicRange.HLG_10_BIT)) {
        vb.setDynamicRange(DynamicRange.HLG_10_BIT)
      }
      vc = vb.build()
    }

    val proc = processor
    val hdrActive = cfg.mode == "video" && cfg.video.hdr
    val useEffect = attempt.effect && proc != null && proc.isHealthy && activeExtension == "none" && !hdrActive
    val softwareStab = cfg.mode == "video" && cfg.video.stabilization == "software"
    var targets = 0
    if (useEffect) {
      targets = CameraEffect.PREVIEW
      if (vc != null && (!cfg.video.clean || softwareStab)) targets = targets or CameraEffect.VIDEO_CAPTURE
    }
    proc?.gradeRecording = !cfg.video.clean
    proc?.setStabilization(useEffect && softwareStab)
    val group = UseCaseGroup.Builder().setViewPort(viewPort).addUseCase(preview)
    ic?.let { group.addUseCase(it) }
    vc?.let { group.addUseCase(it) }
    if (useEffect && proc != null) {
      group.addEffect(GradeEffect(targets, proc, Consumer<Throwable> { t -> main.post { listener.emitError("effect", t.message ?: "Look processing stopped") } }))
    }
    camera = p.bindToLifecycle(lifecycleOwner, selector, group.build())
    imageCapture = ic
    videoCapture = vc
    effectActive = useEffect
    effectTargets = targets
  }

  private fun readyInfo(cam: Camera, cfg: SessionConfigState, notes: List<String>): Map<String, Any?> {
    val info = cam.cameraInfo
    val zs = info.zoomState.value
    val ex = info.exposureState
    val photoRes = imageCapture?.resolutionInfo?.resolution
    val videoRes = videoCapture?.resolutionInfo?.resolution
    val ois = CameraCatalog.hasOis(info) && cfg.video.stabilization != "off"
    val eis = cfg.mode == "video" && cfg.video.stabilization == "enhanced" && !notes.contains("fps") &&
      (videoCapture?.isVideoStabilizationEnabled == true)
    val lookNote = when {
      effectActive -> null
      cfg.mode == "slowmo" -> "slowmo"
      activeExtension != "none" -> "extension"
      cfg.mode == "video" && cfg.video.hdr -> "hdr"
      else -> "gpu"
    }
    return mapOf(
      "cameraId" to CameraCatalog.cameraId(info),
      "mode" to cfg.mode,
      "lens" to CameraCatalog.lensInfo(info).kind,
      "zoom" to (zs?.zoomRatio ?: 1f).toDouble(),
      "zoomMin" to (zs?.minZoomRatio ?: 1f).toDouble(),
      "zoomMax" to (zs?.maxZoomRatio ?: 1f).toDouble(),
      "exposureSupported" to ex.isExposureCompensationSupported,
      "exposureMin" to ex.exposureCompensationRange.lower,
      "exposureMax" to ex.exposureCompensationRange.upper,
      "exposureStep" to ex.exposureCompensationStep.toDouble(),
      "exposureIndex" to ex.exposureCompensationIndex,
      "hasFlash" to info.hasFlashUnit(),
      "liveLook" to effectActive,
      "lookInRecording" to ((effectTargets and CameraEffect.VIDEO_CAPTURE) != 0),
      "lookNote" to lookNote,
      "extension" to activeExtension,
      "photoWidth" to photoRes?.width,
      "photoHeight" to photoRes?.height,
      "videoWidth" to videoRes?.width,
      "videoHeight" to videoRes?.height,
      "videoQuality" to videoCapture?.selectedQuality?.let { CameraCatalog.qualityName(it) },
      "fps" to if (cfg.mode == "video" && !notes.contains("fps")) cfg.video.fps else if (cfg.mode == "slowmo") cfg.video.slowFps else 30,
      "hdr" to (cfg.mode == "video" && videoCapture?.dynamicRange == DynamicRange.HLG_10_BIT),
      "raw" to (imageCapture?.outputFormat == ImageCapture.OUTPUT_FORMAT_RAW_JPEG),
      "ultraHdr" to (imageCapture?.outputFormat == ImageCapture.OUTPUT_FORMAT_JPEG_ULTRA_HDR),
      "ois" to ois,
      "eis" to eis,
      "softwareStabilization" to (effectActive && cfg.mode == "video" && cfg.video.stabilization == "software"),
      "stabilizationCrop" to ((1f - 1f / GradeSurfaceProcessor.ZOOM) * 100f).toDouble(),
      "notes" to notes,
      "macroFocusMode" to (cfg.mode == "macro" && afModes(info).contains(CameraMetadata.CONTROL_AF_MODE_MACRO))
    )
  }

  private fun afModes(info: CameraInfo): IntArray =
    CameraCatalog.characteristic(info, android.hardware.camera2.CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES) ?: IntArray(0)

  private fun attachObservers(info: CameraInfo) {
    observedInfo = info
    info.zoomState.observe(lifecycleOwner, zoomObserver)
    info.cameraState.observe(lifecycleOwner, stateObserver)
  }

  private fun detachObservers() {
    observedInfo?.let {
      it.zoomState.removeObserver(zoomObserver)
      it.cameraState.removeObserver(stateObserver)
    }
    observedInfo = null
  }

  private fun handleCameraState(state: CameraState) {
    val error = state.error ?: return
    val message = when (error.code) {
      CameraState.ERROR_CAMERA_IN_USE -> "Another app is using the camera."
      CameraState.ERROR_MAX_CAMERAS_IN_USE -> "Too many cameras are open. Close other camera apps."
      CameraState.ERROR_CAMERA_DISABLED -> "The camera is disabled by a device policy."
      CameraState.ERROR_CAMERA_FATAL_ERROR -> "The camera stopped responding. Restart the app."
      CameraState.ERROR_DO_NOT_DISTURB_MODE_ENABLED -> "Turn off Do Not Disturb to use the camera."
      CameraState.ERROR_STREAM_CONFIG -> "This combination of settings isn't supported. Try a lower resolution or frame rate."
      else -> "The camera hit a temporary problem and is reconnecting."
    }
    listener.emitError("camera_state_${error.code}", message)
  }

  // ---- Camera2 request options: OIS, macro focus, manual exposure/focus, white balance, locks ----

  private fun applyCaptureOptions() {
    val cam = camera ?: return
    val info = cam.cameraInfo
    val cfg = config
    val b = CaptureRequestOptions.Builder()
    if (CameraCatalog.hasOis(info) && cfg.video.stabilization != "off" && cfg.mode != "slowmo") {
      b.setCaptureRequestOption(CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE, CameraMetadata.LENS_OPTICAL_STABILIZATION_MODE_ON)
    }
    val manualMode = cfg.mode == "pro" || cfg.mode == "macro"
    if (manualMode && CameraCatalog.supportsManualSensor(info) && (manual.iso != null || manual.shutterNs != null)) {
      val iso = manual.iso ?: lastIso
      val exposure = manual.shutterNs ?: lastExposureNs
      b.setCaptureRequestOption(CaptureRequest.CONTROL_AE_MODE, CameraMetadata.CONTROL_AE_MODE_OFF)
      b.setCaptureRequestOption(CaptureRequest.SENSOR_SENSITIVITY, iso)
      b.setCaptureRequestOption(CaptureRequest.SENSOR_EXPOSURE_TIME, exposure)
      b.setCaptureRequestOption(CaptureRequest.SENSOR_FRAME_DURATION, maxOf(exposure, 33_333_333L))
    } else if (manual.aeLock) {
      b.setCaptureRequestOption(CaptureRequest.CONTROL_AE_LOCK, true)
    }
    if (manualMode && manual.focus != null && CameraCatalog.supportsManualFocus(info)) {
      b.setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF)
      b.setCaptureRequestOption(CaptureRequest.LENS_FOCUS_DISTANCE, manual.focus!!.coerceIn(0f, CameraCatalog.minFocusDiopters(info)))
    } else if (cfg.mode == "macro" && !focusLocked && afModes(info).contains(CameraMetadata.CONTROL_AF_MODE_MACRO)) {
      b.setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_MACRO)
    }
    if (manual.awb != "auto") {
      b.setCaptureRequestOption(CaptureRequest.CONTROL_AWB_MODE, CameraCatalog.awbMode(manual.awb))
    }
    if (manual.awbLock) b.setCaptureRequestOption(CaptureRequest.CONTROL_AWB_LOCK, true)
    try {
      Camera2CameraControl.from(cam.cameraControl).setCaptureRequestOptions(b.build())
    } catch (e: Exception) {
      Log.w(TAG, "Capture options rejected", e)
    }
  }

  private val captureCallback = object : CameraCaptureSession.CaptureCallback() {
    override fun onCaptureCompleted(session: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
      result.get(android.hardware.camera2.CaptureResult.SENSOR_SENSITIVITY)?.let { lastIso = it }
      result.get(android.hardware.camera2.CaptureResult.SENSOR_EXPOSURE_TIME)?.let { lastExposureNs = it }
      if (!wantMetadata) return
      val now = SystemClock.elapsedRealtime()
      if (now - lastMetaAt < 250) return
      lastMetaAt = now
      val values = mapOf(
        "iso" to result.get(android.hardware.camera2.CaptureResult.SENSOR_SENSITIVITY),
        "exposureNs" to result.get(android.hardware.camera2.CaptureResult.SENSOR_EXPOSURE_TIME)?.toDouble(),
        "focusDiopters" to result.get(android.hardware.camera2.CaptureResult.LENS_FOCUS_DISTANCE)?.toDouble(),
        "afState" to result.get(android.hardware.camera2.CaptureResult.CONTROL_AF_STATE)
      )
      main.post { if (!destroyed) listener.emitMetadata(values) }
    }
  }

  // ---- controls ----

  fun setZoom(ratio: Float) {
    requestedZoom = ratio
    val cam = camera ?: return
    val zs = cam.cameraInfo.zoomState.value ?: return
    cam.cameraControl.setZoomRatio(ratio.coerceIn(zs.minZoomRatio, zs.maxZoomRatio))
  }

  fun setExposureIndex(index: Int) {
    val cam = camera ?: return
    val range = cam.cameraInfo.exposureState.exposureCompensationRange
    if (!cam.cameraInfo.exposureState.isExposureCompensationSupported) return
    cam.cameraControl.setExposureCompensationIndex(index.coerceIn(range.lower, range.upper))
  }

  fun focusAt(xPx: Float, yPx: Float, lock: Boolean) {
    val cam = camera ?: return
    val point = previewView.meteringPointFactory.createPoint(xPx, yPx)
    val manualFocus = (config.mode == "pro" || config.mode == "macro") && manual.focus != null
    val flags = if (manualFocus) FocusMeteringAction.FLAG_AE else FocusMeteringAction.FLAG_AF or FocusMeteringAction.FLAG_AE
    val builder = FocusMeteringAction.Builder(point, flags)
    if (lock) builder.disableAutoCancel() else builder.setAutoCancelDuration(5, TimeUnit.SECONDS)
    var action = builder.build()
    if (!cam.cameraInfo.isFocusMeteringSupported(action)) {
      action = FocusMeteringAction.Builder(point, FocusMeteringAction.FLAG_AE).build()
    }
    focusLocked = lock
    if (!lock && manual.aeLock) {
      manual = manual.copy(aeLock = false)
      applyCaptureOptions()
    } else if (config.mode == "macro") {
      applyCaptureOptions()
    }
    val future = cam.cameraControl.startFocusAndMetering(action)
    future.addListener({
      val ok = try { future.get().isFocusSuccessful } catch (e: Exception) { false }
      if (lock && ok) {
        manual = manual.copy(aeLock = true)
        applyCaptureOptions()
      }
      listener.emitFocus(mapOf("success" to ok, "locked" to lock))
    }, mainExecutor)
  }

  fun resetFocus() {
    val cam = camera ?: return
    focusLocked = false
    if (manual.aeLock) manual = manual.copy(aeLock = false)
    cam.cameraControl.cancelFocusAndMetering()
    applyCaptureOptions()
  }

  // ---- photos ----

  fun takePhoto(done: (Map<String, Any?>?, String?) -> Unit) {
    val ic = imageCapture
    if (ic == null) {
      done(null, "Switch to a photo mode to take pictures.")
      return
    }
    val cfg = config
    val snapshot = grade
    val front = camera?.cameraInfo?.lensFacing == CameraSelector.LENS_FACING_FRONT
    val name = MediaStoreWriter.newName("IMG", "jpg")
    val tmp = File(captureDir, name)
    val metadata = ImageCapture.Metadata().apply { isReversedHorizontal = front && cfg.photo.mirrorFront }
    val jpegOptions = ImageCapture.OutputFileOptions.Builder(tmp).setMetadata(metadata).build()
    val raw = ic.outputFormat == ImageCapture.OUTPUT_FORMAT_RAW_JPEG
    val ultraHdr = ic.outputFormat == ImageCapture.OUTPUT_FORMAT_JPEG_ULTRA_HDR
    if (cfg.photo.shutterSound || CameraInfo.mustPlayShutterSound()) {
      try { shutterSound.play(MediaActionSound.SHUTTER_CLICK) } catch (_: Exception) {}
    }
    var rawUri: String? = null
    val callback = object : ImageCapture.OnImageSavedCallback {
      override fun onCaptureStarted() {
        main.post { listener.emitPhoto(mapOf("state" to "captured")) }
      }

      override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
        if (raw && outputFileResults.imageFormat == ImageFormat.RAW_SENSOR) {
          val saved = outputFileResults.savedUri
          rawUri = if (saved != null && saved.scheme == "file") {
            MediaStoreWriter.scan(context, File(saved.path ?: ""), "image/x-adobe-dng").toString()
          } else saved?.toString()
          return
        }
        processing.execute { finishPhoto(tmp, snapshot, cfg, ultraHdr, { rawUri }, done) }
      }

      override fun onError(exception: ImageCaptureException) {
        tmp.delete()
        main.post { done(null, exception.message ?: "The photo couldn't be captured.") }
      }
    }
    if (raw) {
      val rawName = name.removeSuffix(".jpg") + ".dng"
      val rawOptions = if (Build.VERSION.SDK_INT >= 29) {
        ImageCapture.OutputFileOptions.Builder(
          context.contentResolver,
          MediaStoreWriter.imageCollection(),
          MediaStoreWriter.imageContentValues(rawName, "image/x-adobe-dng")
        ).build()
      } else {
        ImageCapture.OutputFileOptions.Builder(MediaStoreWriter.legacyImageFile(rawName)).build()
      }
      ic.takePicture(rawOptions, jpegOptions, io, callback)
    } else {
      ic.takePicture(jpegOptions, io, callback)
    }
  }

  private fun finishPhoto(
    tmp: File,
    snapshot: GradeParams,
    cfg: SessionConfigState,
    ultraHdr: Boolean,
    rawUri: () -> String?,
    done: (Map<String, Any?>?, String?) -> Unit
  ) {
    var finalUri: Uri? = null
    var originalUri: Uri? = null
    var warning: String? = null
    try {
      if (snapshot.isNeutral || ultraHdr) {
        finalUri = MediaStoreWriter.saveFile(context, tmp, MediaStoreWriter.Kind.IMAGE, tmp.name, "image/jpeg")
      } else {
        val graded = File(captureDir, tmp.nameWithoutExtension + "_graded.jpg")
        try {
          PhotoRenderer.render(context, Uri.fromFile(tmp), graded, snapshot, EditTransform(), "jpeg", cfg.photo.jpegQuality)
          finalUri = MediaStoreWriter.saveFile(context, graded, MediaStoreWriter.Kind.IMAGE, tmp.name, "image/jpeg")
          if (cfg.photo.keepOriginal) {
            originalUri = MediaStoreWriter.saveFile(
              context, tmp, MediaStoreWriter.Kind.IMAGE,
              tmp.nameWithoutExtension + "_original.jpg", "image/jpeg", MediaStoreWriter.ORIGINALS
            )
          }
        } catch (e: Throwable) {
          Log.w(TAG, "Grading failed, keeping the original", e)
          warning = "The look couldn't be applied, so the original photo was saved."
          finalUri = MediaStoreWriter.saveFile(context, tmp, MediaStoreWriter.Kind.IMAGE, tmp.name, "image/jpeg")
        } finally {
          graded.delete()
        }
      }
      val uri = finalUri!!.toString()
      val thumb = MediaProbe.thumbnail(context, uri, 240)
      val probe = MediaProbe.probe(context, uri)
      tmp.delete()
      val result = mapOf(
        "uri" to uri,
        "thumbnail" to thumb,
        "width" to probe["width"],
        "height" to probe["height"],
        "originalUri" to originalUri?.toString(),
        "rawUri" to rawUri(),
        "warning" to warning
      )
      main.post {
        listener.emitPhoto(mapOf("state" to "saved", "uri" to uri, "thumbnail" to thumb))
        done(result, null)
      }
    } catch (e: Throwable) {
      main.post { done(null, "The photo couldn't be saved: ${e.message}") }
    }
  }

  // ---- video ----

  private fun hasMic(): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

  @SuppressLint("MissingPermission")
  fun startRecording(done: (String?) -> Unit) {
    val cfg = config
    if (cfg.mode == "timelapse") {
      startTimelapse(done)
      return
    }
    val vc = videoCapture
    if (vc == null) {
      done("Switch to video to record.")
      return
    }
    if (recording != null) {
      done(null)
      return
    }
    val free = (MediaProbe.storage()["freeBytes"] as? Long) ?: Long.MAX_VALUE
    if (free < 150L * 1024 * 1024) {
      done("Storage is almost full. Free up space to record.")
      return
    }
    val name = MediaStoreWriter.newName("VID", "mp4", if (cfg.mode == "slowmo") "_SLOMO" else "")
    var pending = if (Build.VERSION.SDK_INT >= 29) {
      vc.output.prepareRecording(
        context,
        MediaStoreOutputOptions.Builder(context.contentResolver, MediaStoreWriter.videoCollection())
          .setContentValues(MediaStoreWriter.videoContentValues(name))
          .build()
      )
    } else {
      vc.output.prepareRecording(context, FileOutputOptions.Builder(MediaStoreWriter.legacyVideoFile(name)).build())
    }
    if (cfg.video.audio && cfg.mode != "slowmo" && hasMic()) pending = pending.withAudioEnabled(false)
    vc.targetRotation = targetRotation
    var lastStatusAt = 0L
    recording = pending.start(mainExecutor) { event ->
      when (event) {
        is VideoRecordEvent.Start -> listener.emitRecording(mapOf("state" to "recording", "durationMs" to 0L))
        is VideoRecordEvent.Pause -> listener.emitRecording(mapOf("state" to "paused", "durationMs" to event.recordingStats.recordedDurationNanos / 1_000_000))
        is VideoRecordEvent.Resume -> listener.emitRecording(mapOf("state" to "recording", "durationMs" to event.recordingStats.recordedDurationNanos / 1_000_000))
        is VideoRecordEvent.Status -> {
          val now = SystemClock.elapsedRealtime()
          if (now - lastStatusAt >= 250) {
            lastStatusAt = now
            listener.emitRecording(
              mapOf(
                "state" to "recording",
                "durationMs" to event.recordingStats.recordedDurationNanos / 1_000_000,
                "bytes" to event.recordingStats.numBytesRecorded
              )
            )
          }
        }
        is VideoRecordEvent.Finalize -> onFinalize(event)
      }
    }
    done(null)
  }

  private fun onFinalize(event: VideoRecordEvent.Finalize) {
    recording = null
    val err = event.error
    val keep = !event.hasError() || err == VideoRecordEvent.Finalize.ERROR_SOURCE_INACTIVE ||
      err == VideoRecordEvent.Finalize.ERROR_INSUFFICIENT_STORAGE ||
      err == VideoRecordEvent.Finalize.ERROR_FILE_SIZE_LIMIT_REACHED ||
      err == VideoRecordEvent.Finalize.ERROR_DURATION_LIMIT_REACHED
    val durationMs = event.recordingStats.recordedDurationNanos / 1_000_000
    val warning = when (err) {
      VideoRecordEvent.Finalize.ERROR_SOURCE_INACTIVE -> "Recording stopped because the camera was interrupted. The clip was saved."
      VideoRecordEvent.Finalize.ERROR_INSUFFICIENT_STORAGE -> "Storage ran out. The clip was saved up to that point."
      else -> null
    }
    val output = event.outputResults.outputUri
    if (keep && output != Uri.EMPTY) {
      io.execute {
        val uri = if (output.scheme == "file") MediaStoreWriter.scan(context, File(output.path ?: ""), "video/mp4") else output
        val thumb = MediaProbe.thumbnail(context, uri.toString(), 240)
        main.post {
          listener.emitRecording(
            mapOf("state" to "saved", "uri" to uri.toString(), "thumbnail" to thumb, "durationMs" to durationMs, "warning" to warning)
          )
        }
      }
    } else {
      listener.emitRecording(mapOf("state" to "error", "message" to recordingError(err, event.cause)))
    }
    if (pendingRebind) {
      pendingRebind = false
      main.post { rebind() }
    }
  }

  private fun recordingError(code: Int, cause: Throwable?): String = when (code) {
    VideoRecordEvent.Finalize.ERROR_NO_VALID_DATA -> "The clip was too short to save."
    VideoRecordEvent.Finalize.ERROR_ENCODING_FAILED -> "The video encoder failed. Try a lower resolution."
    VideoRecordEvent.Finalize.ERROR_INVALID_OUTPUT_OPTIONS -> "The video couldn't be written to storage."
    else -> "Recording failed${cause?.message?.let { ": $it" } ?: "."}"
  }

  fun stopRecording() {
    if (timelapseActive) {
      stopTimelapse()
      return
    }
    recording?.stop()
  }

  fun pauseRecording() { recording?.pause() }
  fun resumeRecording() { recording?.resume() }
  fun muteRecording(muted: Boolean) { recording?.mute(muted) }

  private fun startTimelapse(done: (String?) -> Unit) {
    val proc = processor
    val cam = camera
    if (proc == null || cam == null || !effectActive) {
      done("Time-lapse needs the GPU pipeline, which isn't running.")
      return
    }
    val name = MediaStoreWriter.newName("VID", "mp4", "_TIMELAPSE")
    val opened = try {
      MediaStoreWriter.openForWrite(context, MediaStoreWriter.Kind.VIDEO, name, "video/mp4")
    } catch (e: Exception) {
      done("Couldn't create the video file: ${e.message}")
      return
    }
    val orientation = cam.cameraInfo.getSensorRotationDegrees(targetRotation)
    val input = proc.inputSize
    val intervalNs = config.timelapseIntervalMs.coerceIn(100, 60_000) * 1_000_000L
    proc.startTimelapse({ core ->
      TimelapseEncoder(core, input[0], input[1], orientation, intervalNs, opened.first, opened.second)
    }) { error ->
      main.post {
        if (error != null) {
          try { opened.second.close() } catch (_: Exception) {}
          MediaStoreWriter.delete(context, opened.first)
          done("Time-lapse couldn't start: ${error.message}")
        } else {
          timelapseActive = true
          timelapseStartedAt = SystemClock.elapsedRealtime()
          main.post(timelapseTicker)
          done(null)
        }
      }
    }
  }

  private fun stopTimelapse() {
    val proc = processor ?: return
    timelapseActive = false
    main.removeCallbacks(timelapseTicker)
    listener.emitRecording(mapOf("state" to "saving"))
    proc.stopTimelapse { result ->
      io.execute {
        if (result != null && result.ok) {
          val uri = MediaStoreWriter.publish(context, result.uri, "video/mp4")
          val thumb = MediaProbe.thumbnail(context, uri.toString(), 240)
          main.post {
            listener.emitRecording(mapOf("state" to "saved", "uri" to uri.toString(), "thumbnail" to thumb, "durationMs" to result.durationMs))
          }
        } else {
          result?.let { MediaStoreWriter.delete(context, it.uri) }
          main.post { listener.emitRecording(mapOf("state" to "error", "message" to "Time-lapse needs at least one captured frame.")) }
        }
        if (pendingRebind) {
          pendingRebind = false
          main.post { rebind() }
        }
      }
    }
  }

  val isRecording: Boolean get() = recording != null || timelapseActive

  // ---- lifecycle ----

  fun destroy() {
    if (destroyed) return
    destroyed = true
    orientationListener.disable()
    main.removeCallbacks(timelapseTicker)
    try { recording?.stop() } catch (_: Exception) {}
    recording = null
    if (timelapseActive) {
      timelapseActive = false
      processor?.stopTimelapse { result -> result?.let { if (it.ok) MediaStoreWriter.publish(context, it.uri, "video/mp4") } }
    }
    detachObservers()
    previewView.previewStreamState.removeObserver(streamObserver)
    try { provider?.unbindAll() } catch (_: Exception) {}
    processor?.release()
    processor = null
    try { shutterSound.release() } catch (_: Exception) {}
    io.shutdown()
    processing.shutdown()
  }

  companion object {
    private const val TAG = "CameroSession"
  }
}
