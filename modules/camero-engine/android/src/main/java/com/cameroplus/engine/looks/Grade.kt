package com.cameroplus.engine.looks

import org.json.JSONObject
import java.nio.ByteBuffer
import kotlin.math.abs

/**
 * A grade as sent from JavaScript: a look, its intensity and manual adjustments.
 * Units: exposure in stops (-2..2); fade, grain and sharpness 0..1; everything else -1..1.
 */
data class GradeParams(
  val look: String = LookLibrary.NONE,
  val intensity: Float = 1f,
  val adj: Map<String, Float> = emptyMap()
) {
  private fun a(key: String): Float = adj[key] ?: 0f

  val lookSpec: LookSpec? get() = if (intensity <= 0.001f) null else LookLibrary.find(look)

  val isNeutral: Boolean
    get() = lookSpec == null && adj.values.all { abs(it) < 0.001f }

  fun uniforms(): GradeUniforms {
    val spec = lookSpec
    val k = if (spec != null) intensity.coerceIn(0f, 1f) else 0f
    val extras = spec?.extras
    val vignette = (a("vignette") + (extras?.vignette ?: 0f) * k).coerceIn(-1f, 1f)
    val grain = (a("grain") + (extras?.grain ?: 0f) * k).coerceIn(0f, 1f)
    val clarity = (a("clarity") + (extras?.clarity ?: 0f) * k).coerceIn(-1f, 1f)
    val sharpness = (a("sharpness") + (extras?.sharpness ?: 0f) * k).coerceIn(0f, 1f)
    val dehaze = (a("dehaze") + (extras?.dehaze ?: 0f) * k).coerceIn(-1f, 1f)
    return GradeUniforms(
      tone = floatArrayOf(a("exposure").coerceIn(-3f, 3f), a("brightness"), a("contrast"), a("saturation")),
      tone2 = floatArrayOf(a("vibrance"), a("highlights"), a("shadows"), a("whites")),
      tone3 = floatArrayOf(a("blacks"), a("fade").coerceIn(0f, 1f), vignette, grain),
      detail = floatArrayOf(sharpness, clarity, dehaze),
      wb = LutBuilder.whiteBalance(a("temperature"), a("tint")),
      lutKey = spec?.id,
      lutMix = k,
      lutSize = LutBuilder.SIZE
    )
  }

  fun toJson(): String {
    val o = JSONObject()
    o.put("look", look)
    o.put("intensity", intensity.toDouble())
    val adjJson = JSONObject()
    adj.forEach { (key, v) -> adjJson.put(key, v.toDouble()) }
    o.put("adj", adjJson)
    return o.toString()
  }

  companion object {
    val NEUTRAL = GradeParams()

    val ADJUSTMENT_KEYS = listOf(
      "exposure", "brightness", "contrast", "saturation", "vibrance", "temperature", "tint",
      "highlights", "shadows", "whites", "blacks", "sharpness", "clarity", "fade", "vignette", "grain", "dehaze"
    )

    fun fromJson(json: String?): GradeParams {
      if (json.isNullOrBlank()) return NEUTRAL
      return try {
        val o = JSONObject(json)
        val adjJson = o.optJSONObject("adj")
        val adj = HashMap<String, Float>()
        if (adjJson != null) {
          for (key in ADJUSTMENT_KEYS) {
            if (adjJson.has(key)) adj[key] = adjJson.optDouble(key, 0.0).toFloat()
          }
        }
        GradeParams(
          look = o.optString("look", LookLibrary.NONE).ifBlank { LookLibrary.NONE },
          intensity = o.optDouble("intensity", 1.0).toFloat().coerceIn(0f, 1f),
          adj = adj
        )
      } catch (e: Exception) {
        NEUTRAL
      }
    }
  }
}

/** Uniform values derived from [GradeParams]; packed the way the shader expects them. */
class GradeUniforms(
  val tone: FloatArray,
  val tone2: FloatArray,
  val tone3: FloatArray,
  val detail: FloatArray,
  val wb: FloatArray,
  val lutKey: String?,
  val lutMix: Float,
  val lutSize: Int
) {
  val needsNeighbourhood: Boolean get() = detail[0] > 0.001f || abs(detail[1]) > 0.001f || abs(detail[2]) > 0.001f

  companion object {
    val NEUTRAL: GradeUniforms = GradeParams.NEUTRAL.uniforms()
  }
}

/** Process-wide cache of baked LUTs (about 140 KB each). */
object LutCache {
  private const val MAX_ENTRIES = 10
  private val cache = object : LinkedHashMap<String, ByteBuffer>(16, 0.75f, true) {
    override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, ByteBuffer>?): Boolean = size > MAX_ENTRIES
  }

  @Synchronized
  fun get(lookId: String?): ByteBuffer? {
    val spec = LookLibrary.find(lookId) ?: return null
    cache[spec.id]?.let { return it.duplicate() }
    val built = LutBuilder.build(spec)
    cache[spec.id] = built
    return built.duplicate()
  }

  private val signatures = HashMap<String, List<String>>()

  /** Shadow, midtone and highlight rendering of neutral greys, as hex colours for the UI. */
  @Synchronized
  fun toneSignature(spec: LookSpec): List<String> {
    signatures[spec.id]?.let { return it }
    val result = listOf(0.16f, 0.46f, 0.8f).map { v ->
      val c = LutBuilder.applyOne(spec, v, v, v)
      String.format(java.util.Locale.US, "#%02X%02X%02X", (c[0] * 255).toInt(), (c[1] * 255).toInt(), (c[2] * 255).toInt())
    }
    signatures[spec.id] = result
    return result
  }
}
