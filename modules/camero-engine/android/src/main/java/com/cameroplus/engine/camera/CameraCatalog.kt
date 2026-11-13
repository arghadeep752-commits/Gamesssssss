package com.cameroplus.engine.camera

import android.app.ActivityManager
import android.content.Context
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.Sensor
import android.hardware.SensorManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraMetadata
import android.media.MediaCodecList
import android.opengl.GLES20
import android.os.Build
import android.util.Range
import android.util.Size
import androidx.annotation.OptIn
import androidx.camera.camera2.interop.Camera2CameraInfo
import androidx.camera.camera2.interop.ExperimentalCamera2Interop
import androidx.camera.core.CameraInfo
import androidx.camera.core.CameraSelector
import androidx.camera.core.DynamicRange
import androidx.camera.core.ExperimentalSessionConfig
import androidx.camera.core.ImageCapture
import androidx.camera.core.Preview
import androidx.camera.extensions.ExtensionMode
import androidx.camera.extensions.ExtensionsManager
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.HighSpeedVideoSessionConfig
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.VideoCapture
import com.cameroplus.engine.gl.GlCore
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.roundToInt

/**
 * Reads what each camera can genuinely do. Every option the UI shows comes from this report,
 * so unsupported resolutions, frame rates, lenses or stabilisation modes are never offered.
 */
@OptIn(ExperimentalCamera2Interop::class)
object CameraCatalog {
  val QUALITY_ORDER = listOf(Quality.UHD, Quality.FHD, Quality.HD, Quality.SD)
  private val FPS_CANDIDATES = listOf(24, 25, 30, 50, 60)

  fun qualityName(q: Quality): String = when (q) {
    Quality.UHD -> "UHD"
    Quality.FHD -> "FHD"
    Quality.HD -> "HD"
    Quality.SD -> "SD"
    else -> "OTHER"
  }

  fun qualityFromName(name: String?): Quality = when (name) {
    "UHD" -> Quality.UHD
    "HD" -> Quality.HD
    "SD" -> Quality.SD
    else -> Quality.FHD
  }

  fun cameraId(info: CameraInfo): String = try {
    Camera2CameraInfo.from(info).cameraId
  } catch (e: Exception) {
    "?"
  }

  fun <T> characteristic(info: CameraInfo, key: CameraCharacteristics.Key<T>): T? = try {
    Camera2CameraInfo.from(info).getCameraCharacteristic(key)
  } catch (e: Exception) {
    null
  }

  fun hasOis(info: CameraInfo): Boolean =
    characteristic(info, CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)
      ?.contains(CameraMetadata.LENS_OPTICAL_STABILIZATION_MODE_ON) == true

  fun hasEis(info: CameraInfo): Boolean =
    characteristic(info, CameraCharacteristics.CONTROL_AVAILABLE_VIDEO_STABILIZATION_MODES)
      ?.contains(CameraMetadata.CONTROL_VIDEO_STABILIZATION_MODE_ON) == true

  fun capabilities(info: CameraInfo): IntArray =
    characteristic(info, CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES) ?: IntArray(0)

  fun supportsManualSensor(info: CameraInfo): Boolean =
    capabilities(info).contains(CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR)

  fun minFocusDiopters(info: CameraInfo): Float =
    characteristic(info, CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE) ?: 0f

  fun supportsManualFocus(info: CameraInfo): Boolean {
    val afModes = characteristic(info, CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES) ?: IntArray(0)
    return minFocusDiopters(info) > 0f && afModes.contains(CameraMetadata.CONTROL_AF_MODE_OFF)
  }

  /** Fixed frame rates (24/25/30/50/60) the camera can deliver at [size] for recording. */
  fun frameRatesFor(info: CameraInfo, size: Size?): List<Int> {
    val ranges = try { info.supportedFrameRateRanges } catch (e: Exception) { emptySet<Range<Int>>() }
    val map = characteristic(info, CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
    val maxFps = if (size != null && map != null) {
      val d = try { map.getOutputMinFrameDuration(SurfaceTexture::class.java, size) } catch (e: Exception) { 0L }
      if (d > 0) 1_000_000_000.0 / d else 30.0
    } else 30.0
    return FPS_CANDIDATES.filter { fps ->
      val fixed = ranges.any { it.lower == fps && it.upper == fps }
      val ok = fixed || (fps == 30 && ranges.any { it.upper == 30 })
      ok && maxFps + 0.5 >= fps
    }
  }

  private fun megapixels(size: Size?): Double = if (size == null) 0.0 else size.width.toDouble() * size.height / 1_000_000.0

  private fun largest(sizes: Array<Size>?): Size? = sizes?.maxByOrNull { it.width.toLong() * it.height }

  data class LensInfo(val kind: String, val eqFocal: Float?, val minFocusCm: Float?, val fixedFocus: Boolean)

  fun lensInfo(info: CameraInfo): LensInfo {
    val facing = info.lensFacing
    val focal = characteristic(info, CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.firstOrNull()
    val sensor = characteristic(info, CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)
    val eq = if (focal != null && sensor != null && sensor.width > 0f) {
      (focal * 43.27f / hypot(sensor.width, sensor.height))
    } else null
    val minFocus = minFocusDiopters(info)
    val hyper = characteristic(info, CameraCharacteristics.LENS_INFO_HYPERFOCAL_DISTANCE) ?: 0f
    val calibration = characteristic(info, CameraCharacteristics.LENS_INFO_FOCUS_DISTANCE_CALIBRATION)
      ?: CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_UNCALIBRATED
    val calibrated = calibration != CameraMetadata.LENS_INFO_FOCUS_DISTANCE_CALIBRATION_UNCALIBRATED
    val fixedFocus = minFocus <= 0f
    val intrinsic = try { info.intrinsicZoomRatio } catch (e: Exception) { 1f }
    val depthOnly = capabilities(info).contains(CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_DEPTH_OUTPUT) &&
      !capabilities(info).contains(CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE)
    val macro = facing == CameraSelector.LENS_FACING_BACK && !depthOnly &&
      ((fixedFocus && hyper >= 10f) || (calibrated && minFocus >= 25f))
    val kind = when {
      facing == CameraSelector.LENS_FACING_FRONT -> "front"
      macro -> "macro"
      intrinsic < 0.8f || (eq != null && eq < 20f) -> "ultrawide"
      intrinsic > 1.6f || (eq != null && eq > 45f) -> "tele"
      else -> "wide"
    }
    val minFocusCm = if (!fixedFocus && calibrated) (100f / minFocus) else if (fixedFocus && hyper >= 10f && calibrated) 100f / hyper else null
    return LensInfo(kind, eq, minFocusCm, fixedFocus)
  }

  @kotlin.OptIn(ExperimentalSessionConfig::class)
  fun describeCamera(info: CameraInfo, extensions: ExtensionsManager?): Map<String, Any?> {
    val out = HashMap<String, Any?>()
    val lens = lensInfo(info)
    out["id"] = cameraId(info)
    out["facing"] = when (info.lensFacing) {
      CameraSelector.LENS_FACING_FRONT -> "front"
      CameraSelector.LENS_FACING_BACK -> "back"
      else -> "external"
    }
    out["lens"] = lens.kind
    out["eqFocalLength"] = lens.eqFocal?.let { (it * 10).roundToInt() / 10.0 }
    out["focalLength"] = characteristic(info, CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.firstOrNull()?.toDouble()
    out["aperture"] = characteristic(info, CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES)?.firstOrNull()?.toDouble()
    out["minFocusCm"] = lens.minFocusCm?.let { (it * 10).roundToInt() / 10.0 }
    out["fixedFocus"] = lens.fixedFocus
    out["intrinsicZoom"] = try { info.intrinsicZoomRatio.toDouble() } catch (e: Exception) { 1.0 }
    out["sensorOrientation"] = info.sensorRotationDegrees
    out["hasFlash"] = info.hasFlashUnit()
    out["hardwareLevel"] = when (characteristic(info, CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)) {
      CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "legacy"
      CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "limited"
      CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "full"
      CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "level3"
      CameraMetadata.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "external"
      else -> "unknown"
    }

    val zoom = info.zoomState.value
    val zoomRange = if (Build.VERSION.SDK_INT >= 30) characteristic(info, CameraCharacteristics.CONTROL_ZOOM_RATIO_RANGE) else null
    val maxDigital = characteristic(info, CameraCharacteristics.SCALER_AVAILABLE_MAX_DIGITAL_ZOOM) ?: 1f
    out["zoomMin"] = (zoom?.minZoomRatio ?: zoomRange?.lower ?: 1f).toDouble()
    out["zoomMax"] = (zoom?.maxZoomRatio ?: zoomRange?.upper ?: maxDigital).toDouble()
    val physical = try { info.physicalCameraInfos } catch (e: Exception) { emptySet<CameraInfo>() }
    out["logicalMultiCamera"] = try { info.isLogicalMultiCameraSupported } catch (e: Exception) { false }
    out["opticalStops"] = physical.mapNotNull { p ->
      val r = try { p.intrinsicZoomRatio } catch (e: Exception) { return@mapNotNull null }
      if (r > 0f) (r * 100).roundToInt() / 100.0 else null
    }.distinct().sorted()

    val exposure = info.exposureState
    out["exposureSupported"] = exposure.isExposureCompensationSupported
    out["exposureMin"] = exposure.exposureCompensationRange.lower
    out["exposureMax"] = exposure.exposureCompensationRange.upper
    out["exposureStep"] = exposure.exposureCompensationStep.toDouble()

    val manualSensor = supportsManualSensor(info)
    out["manualSensor"] = manualSensor
    out["manualFocus"] = supportsManualFocus(info)
    out["minFocusDiopters"] = minFocusDiopters(info).toDouble()
    characteristic(info, CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE)?.let {
      out["isoMin"] = it.lower; out["isoMax"] = it.upper
    }
    characteristic(info, CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE)?.let {
      out["shutterMinNs"] = it.lower.toDouble(); out["shutterMaxNs"] = minOf(it.upper, 1_000_000_000L).toDouble()
    }
    val awb = characteristic(info, CameraCharacteristics.CONTROL_AWB_AVAILABLE_MODES) ?: IntArray(0)
    out["awbModes"] = awb.mapNotNull { awbName(it) }
    out["awbLock"] = characteristic(info, CameraCharacteristics.CONTROL_AWB_LOCK_AVAILABLE) == true
    out["aeLock"] = characteristic(info, CameraCharacteristics.CONTROL_AE_LOCK_AVAILABLE) == true

    out["ois"] = hasOis(info)
    out["eis"] = hasEis(info)
    out["previewStabilization"] = try { Preview.getPreviewCapabilities(info).isStabilizationSupported } catch (e: Exception) { false }

    val imageFormats = try { ImageCapture.getImageCaptureCapabilities(info).supportedOutputFormats } catch (e: Exception) { emptySet<Int>() }
    out["raw"] = imageFormats.contains(ImageCapture.OUTPUT_FORMAT_RAW_JPEG)
    out["ultraHdr"] = imageFormats.contains(ImageCapture.OUTPUT_FORMAT_JPEG_ULTRA_HDR)

    val map = characteristic(info, CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
    val maxPhoto = largest(map?.getOutputSizes(ImageFormat.JPEG))
    val highRes = largest(map?.getHighResolutionOutputSizes(ImageFormat.JPEG))
    out["photoMax"] = maxPhoto?.let { mapOf("width" to it.width, "height" to it.height, "mp" to (megapixels(it) * 10).roundToInt() / 10.0) }
    out["photoHighRes"] = if (highRes != null && megapixels(highRes) > megapixels(maxPhoto) + 0.5) {
      mapOf("width" to highRes.width, "height" to highRes.height, "mp" to (megapixels(highRes) * 10).roundToInt() / 10.0)
    } else null

    val videoCaps = Recorder.getVideoCapabilities(info)
    out["videoStabilization"] = try { videoCaps.isStabilizationSupported } catch (e: Exception) { false }
    val qualities = try { videoCaps.getSupportedQualities(DynamicRange.SDR) } catch (e: Exception) { emptyList<Quality>() }
    out["video"] = QUALITY_ORDER.filter { qualities.contains(it) }.map { q ->
      val size = try { QualitySelector.getResolution(info, q) } catch (e: Exception) { null }
      mapOf(
        "quality" to qualityName(q),
        "width" to (size?.width ?: 0),
        "height" to (size?.height ?: 0),
        "fps" to frameRatesFor(info, size)
      )
    }
    out["hdrVideo"] = try { videoCaps.supportedDynamicRanges.contains(DynamicRange.HLG_10_BIT) } catch (e: Exception) { false }
    out["hdrQualities"] = try {
      QUALITY_ORDER.filter { videoCaps.getSupportedQualities(DynamicRange.HLG_10_BIT).contains(it) }.map { qualityName(it) }
    } catch (e: Exception) { emptyList<String>() }

    out["highSpeed"] = try {
      val hs = Recorder.getHighSpeedVideoCapabilities(info)
      if (hs == null) null else {
        val hsQualities = hs.getSupportedQualities(DynamicRange.SDR)
        val probe = HighSpeedVideoSessionConfig(VideoCapture.withOutput(Recorder.Builder().build()), Preview.Builder().build())
        val rates = info.getSupportedFrameRateRanges(probe).map { it.upper }.filter { it >= 100 }.distinct().sorted()
        if (rates.isEmpty() || hsQualities.isEmpty()) null else mapOf(
          "qualities" to QUALITY_ORDER.filter { hsQualities.contains(it) }.map { qualityName(it) },
          "fps" to rates
        )
      }
    } catch (e: Throwable) {
      null
    }

    out["extensions"] = if (extensions == null) emptyList<String>() else listOf(
      ExtensionMode.BOKEH to "bokeh",
      ExtensionMode.HDR to "hdr",
      ExtensionMode.NIGHT to "night",
      ExtensionMode.AUTO to "auto"
    ).filter { (mode, _) ->
      try { extensions.isExtensionAvailable(info.cameraSelector, mode) } catch (e: Exception) { false }
    }.map { it.second }
    return out
  }

  fun awbName(mode: Int): String? = when (mode) {
    CameraMetadata.CONTROL_AWB_MODE_AUTO -> "auto"
    CameraMetadata.CONTROL_AWB_MODE_INCANDESCENT -> "incandescent"
    CameraMetadata.CONTROL_AWB_MODE_FLUORESCENT -> "fluorescent"
    CameraMetadata.CONTROL_AWB_MODE_WARM_FLUORESCENT -> "warm-fluorescent"
    CameraMetadata.CONTROL_AWB_MODE_DAYLIGHT -> "daylight"
    CameraMetadata.CONTROL_AWB_MODE_CLOUDY_DAYLIGHT -> "cloudy"
    CameraMetadata.CONTROL_AWB_MODE_TWILIGHT -> "twilight"
    CameraMetadata.CONTROL_AWB_MODE_SHADE -> "shade"
    else -> null
  }

  fun awbMode(name: String?): Int = when (name) {
    "incandescent" -> CameraMetadata.CONTROL_AWB_MODE_INCANDESCENT
    "fluorescent" -> CameraMetadata.CONTROL_AWB_MODE_FLUORESCENT
    "warm-fluorescent" -> CameraMetadata.CONTROL_AWB_MODE_WARM_FLUORESCENT
    "daylight" -> CameraMetadata.CONTROL_AWB_MODE_DAYLIGHT
    "cloudy" -> CameraMetadata.CONTROL_AWB_MODE_CLOUDY_DAYLIGHT
    "twilight" -> CameraMetadata.CONTROL_AWB_MODE_TWILIGHT
    "shade" -> CameraMetadata.CONTROL_AWB_MODE_SHADE
    else -> CameraMetadata.CONTROL_AWB_MODE_AUTO
  }

  fun describe(context: Context, provider: ProcessCameraProvider, extensions: ExtensionsManager?): Map<String, Any?> {
    val cameras = provider.availableCameraInfos.map { describeCamera(it, extensions) }
    return mapOf(
      "cameras" to cameras,
      "device" to device(context),
      "codecs" to codecs()
    )
  }

  fun device(context: Context): Map<String, Any?> {
    val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    val mem = ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
    val sensors = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    val totalMb = mem.totalMem / (1024 * 1024)
    var renderer: String? = null
    var maxTexture = 0
    try {
      val core = GlCore(recordable = false)
      renderer = GLES20.glGetString(GLES20.GL_RENDERER)
      maxTexture = GlCore.maxTextureSize()
      core.release()
    } catch (_: Exception) {
    }
    val tier = when {
      am.isLowRamDevice || totalMb < 3500 || Build.VERSION.SDK_INT < 28 -> "low"
      totalMb < 6500 -> "mid"
      else -> "high"
    }
    return mapOf(
      "manufacturer" to Build.MANUFACTURER,
      "model" to Build.MODEL,
      "sdk" to Build.VERSION.SDK_INT,
      "release" to Build.VERSION.RELEASE,
      "totalRamMb" to totalMb,
      "lowRam" to am.isLowRamDevice,
      "tier" to tier,
      "gpu" to renderer,
      "maxTextureSize" to maxTexture,
      "gyroscope" to (sensors.getDefaultSensor(Sensor.TYPE_GYROSCOPE) != null),
      "accelerometer" to (sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER) != null)
    )
  }

  fun hevcEncoderAvailable(): Boolean = try {
    MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.any { info ->
      info.isEncoder && info.supportedTypes.any { it.equals("video/hevc", ignoreCase = true) }
    }
  } catch (e: Exception) {
    false
  }

  fun codecs(): Map<String, Any?> {
    val list: List<android.media.MediaCodecInfo> = try {
      MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.toList()
    } catch (e: Exception) {
      emptyList()
    }
    fun maxSize(mime: String): String? {
      val enc = list.filter { it.isEncoder && it.supportedTypes.any { t -> t.equals(mime, ignoreCase = true) } }
      var best: String? = null
      var bestArea = 0
      for (codec in enc) {
        try {
          val caps = codec.getCapabilitiesForType(mime).videoCapabilities ?: continue
          val w = caps.supportedWidths.upper
          val h = caps.getSupportedHeightsFor(minOf(w, caps.supportedWidths.upper)).upper
          if (w * h > bestArea) {
            bestArea = w * h
            best = "${w}x$h"
          }
        } catch (_: Exception) {
        }
      }
      return best
    }
    return mapOf(
      "h264" to (maxSize("video/avc") != null),
      "h264Max" to maxSize("video/avc"),
      "hevc" to (maxSize("video/hevc") != null),
      "hevcMax" to maxSize("video/hevc")
    )
  }

  @Suppress("unused")
  private fun near(a: Float, b: Float) = abs(a - b) < 0.02f
}
