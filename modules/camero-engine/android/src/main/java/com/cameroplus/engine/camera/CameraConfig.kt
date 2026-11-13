package com.cameroplus.engine.camera

import org.json.JSONObject

data class PhotoConfig(
  val resolution: String = "max",
  val jpegQuality: Int = 95,
  val format: String = "jpeg",
  val extension: String = "none",
  val keepOriginal: Boolean = true,
  val shutterSound: Boolean = false,
  val mirrorFront: Boolean = true
) {
  companion object {
    fun fromJson(json: String?): PhotoConfig {
      if (json.isNullOrBlank()) return PhotoConfig()
      return try {
        val o = JSONObject(json)
        PhotoConfig(
          resolution = o.optString("resolution", "max"),
          jpegQuality = o.optInt("jpegQuality", 95).coerceIn(50, 100),
          format = o.optString("format", "jpeg"),
          extension = o.optString("extension", "none"),
          keepOriginal = o.optBoolean("keepOriginal", true),
          shutterSound = o.optBoolean("shutterSound", false),
          mirrorFront = o.optBoolean("mirrorFront", true)
        )
      } catch (e: Exception) {
        PhotoConfig()
      }
    }
  }
}

data class VideoConfig(
  val quality: String = "FHD",
  val fps: Int = 30,
  val hdr: Boolean = false,
  val stabilization: String = "standard",
  val bitrate: String = "auto",
  val audio: Boolean = true,
  val clean: Boolean = false,
  val slowFps: Int = 120
) {
  companion object {
    fun fromJson(json: String?): VideoConfig {
      if (json.isNullOrBlank()) return VideoConfig()
      return try {
        val o = JSONObject(json)
        VideoConfig(
          quality = o.optString("quality", "FHD"),
          fps = o.optInt("fps", 30),
          hdr = o.optBoolean("hdr", false),
          stabilization = o.optString("stabilization", "standard"),
          bitrate = o.optString("bitrate", "auto"),
          audio = o.optBoolean("audio", true),
          clean = o.optBoolean("clean", false),
          slowFps = o.optInt("slowFps", 120)
        )
      } catch (e: Exception) {
        VideoConfig()
      }
    }
  }
}

data class ManualConfig(
  val iso: Int? = null,
  val shutterNs: Long? = null,
  val focus: Float? = null,
  val awb: String = "auto",
  val aeLock: Boolean = false,
  val awbLock: Boolean = false
) {
  companion object {
    fun fromJson(json: String?): ManualConfig {
      if (json.isNullOrBlank()) return ManualConfig()
      return try {
        val o = JSONObject(json)
        ManualConfig(
          iso = if (o.isNull("iso") || !o.has("iso")) null else o.optInt("iso"),
          shutterNs = if (o.isNull("shutterNs") || !o.has("shutterNs")) null else o.optLong("shutterNs"),
          focus = if (o.isNull("focus") || !o.has("focus")) null else o.optDouble("focus").toFloat(),
          awb = o.optString("awb", "auto"),
          aeLock = o.optBoolean("aeLock", false),
          awbLock = o.optBoolean("awbLock", false)
        )
      } catch (e: Exception) {
        ManualConfig()
      }
    }
  }
}

data class SessionConfigState(
  val cameraId: String? = null,
  val mode: String = "photo",
  val aspect: String = "4:3",
  val photo: PhotoConfig = PhotoConfig(),
  val video: VideoConfig = VideoConfig(),
  val timelapseIntervalMs: Int = 1000
) {
  val isVideoMode: Boolean get() = mode == "video" || mode == "slowmo" || mode == "timelapse"

  fun bindKey(extensionsReady: Boolean): String = listOf(
    cameraId, mode, if (isVideoMode) "16:9" else aspect,
    photo.resolution, photo.format, photo.extension, photo.jpegQuality,
    video.quality, video.fps, video.hdr, video.stabilization, video.bitrate, video.clean, video.slowFps,
    extensionsReady
  ).joinToString("|")
}
