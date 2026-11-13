package com.cameroplus.engine.looks

/** Hue-band adjustment in OkLCh. Angles in degrees, chroma multiplier, lightness offset. */
class HueBand(
  val hue: Float,
  val width: Float = 30f,
  val shift: Float = 0f,
  val sat: Float = 1f,
  val lum: Float = 0f
)

/** Colour pushed into a tonal range, as an OkLab hue angle and chroma amount (about 0..0.05). */
class Tint(val hue: Float, val amount: Float)

/** Spatial effects that a LUT cannot express; added to the user's adjustments, scaled by intensity. */
class LookExtras(
  val vignette: Float = 0f,
  val grain: Float = 0f,
  val clarity: Float = 0f,
  val sharpness: Float = 0f,
  val dehaze: Float = 0f
)

/**
 * Parameters for one colour grade. Every look in Camero Plus is defined here as numbers and baked
 * into a 3D LUT on the device; there are no third-party filter assets.
 */
class LookSpec(
  val id: String,
  val name: String,
  val collection: String,
  val exposure: Float = 0f,
  val temperature: Float = 0f,
  val tint: Float = 0f,
  val mixer: FloatArray? = null,
  val shoulder: Float = 0f,
  val contrast: Float = 0f,
  val pivot: Float = 0.45f,
  val curveRgb: FloatArray? = null,
  val curveR: FloatArray? = null,
  val curveG: FloatArray? = null,
  val curveB: FloatArray? = null,
  val saturation: Float = 0f,
  val vibrance: Float = 0f,
  val shadowSat: Float = 1f,
  val highlightSat: Float = 1f,
  val skinProtect: Float = 0.5f,
  val bands: List<HueBand> = emptyList(),
  val shadowTint: Tint? = null,
  val highlightTint: Tint? = null,
  val splitBalance: Float = 0f,
  val blackLift: Float = 0f,
  val whitePoint: Float = 1f,
  val extras: LookExtras = LookExtras()
)

object LookLibrary {
  const val NONE = "none"

  private fun pts(vararg v: Float) = v

  val collections = listOf("Natural", "Everyday", "Cinematic", "Photography", "Film")

  val looks: List<LookSpec> = listOf(
    // Natural
    LookSpec("natural", "Natural", "Natural", contrast = 0.08f, shoulder = 0.25f, vibrance = 0.08f),
    LookSpec("true-color", "True Color", "Natural", contrast = 0.03f, shoulder = 0.12f, skinProtect = 0.3f),
    LookSpec(
      "soft-natural", "Soft Natural", "Natural",
      contrast = -0.14f, shoulder = 0.4f, blackLift = 0.025f, saturation = -0.05f, vibrance = 0.06f, temperature = 0.03f
    ),
    LookSpec(
      "vivid", "Vivid", "Natural",
      contrast = 0.16f, saturation = 0.14f, vibrance = 0.22f, skinProtect = 0.7f, shoulder = 0.2f,
      bands = listOf(HueBand(255f, 35f, sat = 1.08f))
    ),
    LookSpec(
      "warm-natural", "Warm Natural", "Natural",
      temperature = 0.22f, tint = 0.04f, contrast = 0.06f, vibrance = 0.06f, shoulder = 0.2f
    ),
    LookSpec(
      "cool-natural", "Cool Natural", "Natural",
      temperature = -0.2f, tint = -0.02f, contrast = 0.06f, shoulder = 0.2f, highlightTint = Tint(230f, 0.008f)
    ),

    // Everyday
    LookSpec("clean", "Clean", "Everyday", contrast = 0.1f, shoulder = 0.18f, saturation = 0.03f, temperature = -0.03f),
    LookSpec(
      "rich-warm", "Rich Warm", "Everyday",
      contrast = 0.24f, pivot = 0.42f, temperature = 0.16f, tint = 0.03f, saturation = 0.08f, shadowSat = 1.08f,
      shoulder = 0.3f, bands = listOf(HueBand(60f, 30f, sat = 1.06f))
    ),
    LookSpec(
      "rich-cool", "Rich Cool", "Everyday",
      contrast = 0.24f, pivot = 0.42f, temperature = -0.15f, tint = -0.02f, saturation = 0.04f, shoulder = 0.3f,
      bands = listOf(HueBand(250f, 35f, sat = 1.08f, lum = -0.02f))
    ),
    LookSpec(
      "soft-contrast", "Soft Contrast", "Everyday",
      contrast = -0.16f, shoulder = 0.35f, blackLift = 0.02f, vibrance = 0.05f
    ),
    LookSpec(
      "vibrant", "Vibrant", "Everyday",
      vibrance = 0.32f, saturation = 0.06f, contrast = 0.1f, skinProtect = 0.75f, shoulder = 0.18f
    ),
    LookSpec("neutral", "Neutral", "Everyday", contrast = -0.03f, saturation = -0.06f, shoulder = 0.3f, skinProtect = 0.4f),

    // Cinematic
    LookSpec(
      "hollywood", "Hollywood", "Cinematic",
      contrast = 0.22f, pivot = 0.43f, shoulder = 0.45f, saturation = -0.04f, skinProtect = 0.8f,
      bands = listOf(
        HueBand(142f, 35f, shift = 18f, sat = 0.9f),
        HueBand(250f, 35f, shift = -10f, sat = 1.05f),
        HueBand(55f, 25f, sat = 1.08f)
      ),
      shadowTint = Tint(205f, 0.022f), highlightTint = Tint(65f, 0.012f)
    ),
    LookSpec(
      "teal-orange", "Teal & Orange", "Cinematic",
      contrast = 0.18f, shoulder = 0.4f, saturation = 0.04f, skinProtect = 0.85f,
      bands = listOf(
        HueBand(140f, 40f, shift = 38f, sat = 0.85f),
        HueBand(105f, 25f, shift = -20f, sat = 1.05f),
        HueBand(225f, 45f, shift = -22f, sat = 1.1f),
        HueBand(55f, 28f, sat = 1.15f)
      ),
      shadowTint = Tint(210f, 0.035f), highlightTint = Tint(60f, 0.03f)
    ),
    LookSpec(
      "filmic-warm", "Filmic Warm", "Cinematic",
      temperature = 0.18f, contrast = 0.14f, shoulder = 0.5f, blackLift = 0.018f, saturation = -0.02f,
      highlightTint = Tint(70f, 0.02f), shadowTint = Tint(40f, 0.01f),
      curveR = pts(0f, 0f, 0.5f, 0.52f, 1f, 1f)
    ),
    LookSpec(
      "dark-cinema", "Dark Cinema", "Cinematic",
      exposure = -0.3f, contrast = 0.32f, pivot = 0.4f, shoulder = 0.35f, shadowSat = 0.7f, saturation = -0.08f,
      shadowTint = Tint(220f, 0.02f), highlightTint = Tint(70f, 0.012f), extras = LookExtras(vignette = 0.22f)
    ),
    LookSpec(
      "moody-blue", "Moody Blue", "Cinematic",
      temperature = -0.24f, tint = -0.03f, contrast = 0.16f, saturation = -0.18f, highlightSat = 0.75f,
      shoulder = 0.3f, blackLift = 0.012f, shadowTint = Tint(245f, 0.03f),
      bands = listOf(HueBand(55f, 25f, sat = 0.92f), HueBand(250f, 35f, sat = 1.1f))
    ),
    LookSpec(
      "vintage-film", "Vintage Film", "Cinematic",
      blackLift = 0.06f, whitePoint = 0.95f, contrast = 0.06f, shoulder = 0.45f, saturation = -0.12f,
      temperature = 0.12f, highlightTint = Tint(85f, 0.02f),
      curveR = pts(0f, 0.04f, 0.5f, 0.53f, 1f, 0.98f),
      curveB = pts(0f, 0.06f, 0.5f, 0.47f, 1f, 0.9f),
      extras = LookExtras(grain = 0.25f, vignette = 0.2f)
    ),
    LookSpec(
      "golden-hour", "Golden Hour", "Cinematic",
      temperature = 0.34f, tint = 0.06f, contrast = 0.08f, shoulder = 0.32f, saturation = 0.08f,
      highlightTint = Tint(75f, 0.03f),
      bands = listOf(HueBand(55f, 28f, sat = 1.1f, lum = 0.01f), HueBand(250f, 35f, sat = 0.9f))
    ),
    LookSpec(
      "desaturated-cinema", "Desaturated Cinema", "Cinematic",
      saturation = -0.38f, contrast = 0.2f, shoulder = 0.35f, skinProtect = 0.6f, highlightSat = 0.85f,
      shadowTint = Tint(210f, 0.012f)
    ),
    LookSpec(
      "deep-shadows", "Deep Shadows", "Cinematic",
      contrast = 0.3f, pivot = 0.5f, shadowSat = 0.8f, shoulder = 0.25f,
      curveRgb = pts(0f, 0f, 0.25f, 0.17f, 0.5f, 0.48f, 1f, 1f)
    ),
    LookSpec(
      "soft-highlights", "Soft Highlights", "Cinematic",
      shoulder = 0.85f, whitePoint = 0.97f, contrast = 0.04f, highlightSat = 0.85f, blackLift = 0.008f
    ),

    // Photography
    LookSpec(
      "portrait-soft", "Portrait Soft", "Photography",
      contrast = -0.1f, shoulder = 0.35f, temperature = 0.06f, vibrance = 0.06f, skinProtect = 0.9f,
      bands = listOf(HueBand(52f, 30f, shift = -2f, sat = 0.9f, lum = 0.015f)),
      extras = LookExtras(clarity = -0.18f)
    ),
    LookSpec(
      "macro-detail", "Macro Detail", "Photography",
      contrast = 0.1f, vibrance = 0.16f, shoulder = 0.2f,
      extras = LookExtras(clarity = 0.22f, sharpness = 0.22f)
    ),
    LookSpec(
      "nature", "Nature", "Photography",
      vibrance = 0.16f, contrast = 0.1f, shoulder = 0.2f,
      bands = listOf(
        HueBand(140f, 35f, shift = -6f, sat = 1.18f, lum = -0.01f),
        HueBand(110f, 25f, sat = 1.08f),
        HueBand(250f, 35f, sat = 1.1f, lum = -0.02f)
      )
    ),
    LookSpec(
      "landscape", "Landscape", "Photography",
      contrast = 0.14f, shoulder = 0.3f,
      bands = listOf(HueBand(235f, 40f, sat = 1.15f, lum = -0.05f), HueBand(140f, 35f, sat = 1.1f)),
      extras = LookExtras(clarity = 0.15f, dehaze = 0.1f)
    ),
    LookSpec(
      "food", "Food Photography", "Photography",
      temperature = 0.1f, exposure = 0.08f, saturation = 0.1f, contrast = 0.08f, shoulder = 0.22f,
      bands = listOf(
        HueBand(30f, 25f, sat = 1.1f),
        HueBand(60f, 25f, sat = 1.12f),
        HueBand(105f, 25f, sat = 1.08f),
        HueBand(140f, 30f, sat = 1.05f),
        HueBand(250f, 35f, sat = 0.85f)
      )
    ),
    LookSpec(
      "street", "Street Photography", "Photography",
      contrast = 0.26f, saturation = -0.22f, temperature = -0.04f, shoulder = 0.25f,
      extras = LookExtras(grain = 0.12f, clarity = 0.12f, vignette = 0.12f)
    ),
    LookSpec(
      "night", "Night Photography", "Photography",
      contrast = 0.12f, shadowSat = 0.55f, shoulder = 0.55f, temperature = -0.08f,
      highlightTint = Tint(60f, 0.015f), shadowTint = Tint(240f, 0.015f),
      bands = listOf(HueBand(300f, 40f, sat = 1.1f))
    ),

    // Film
    LookSpec(
      "analog-film", "Analog Film", "Film",
      blackLift = 0.035f, shoulder = 0.55f, contrast = 0.1f, saturation = -0.05f,
      bands = listOf(HueBand(140f, 35f, shift = 10f, sat = 0.92f), HueBand(30f, 20f, shift = 4f)),
      curveB = pts(0f, 0.03f, 0.5f, 0.49f, 1f, 0.97f),
      extras = LookExtras(grain = 0.18f)
    ),
    LookSpec(
      "retro-film", "Retro Film", "Film",
      blackLift = 0.07f, whitePoint = 0.94f, temperature = 0.2f, tint = 0.05f, saturation = -0.14f, contrast = 0.04f,
      shadowTint = Tint(330f, 0.02f), highlightTint = Tint(90f, 0.03f),
      extras = LookExtras(grain = 0.22f, vignette = 0.16f)
    ),
    LookSpec(
      "matte-film", "Matte Film", "Film",
      blackLift = 0.1f, whitePoint = 0.93f, contrast = 0.08f, saturation = -0.08f, shoulder = 0.3f
    ),
    LookSpec(
      "classic-film", "Classic Film", "Film",
      contrast = 0.26f, saturation = 0.14f, shoulder = 0.25f, skinProtect = 0.6f,
      bands = listOf(HueBand(255f, 35f, sat = 1.15f, lum = -0.03f), HueBand(30f, 22f, sat = 1.08f)),
      shadowTint = Tint(250f, 0.012f), extras = LookExtras(grain = 0.1f)
    ),
    LookSpec(
      "warm-film", "Warm Film", "Film",
      temperature = 0.22f, blackLift = 0.03f, shoulder = 0.4f, contrast = 0.08f,
      highlightTint = Tint(75f, 0.022f), extras = LookExtras(grain = 0.12f)
    ),
    LookSpec(
      "cool-film", "Cool Film", "Film",
      temperature = -0.18f, blackLift = 0.03f, shoulder = 0.4f, contrast = 0.08f, saturation = -0.04f,
      shadowTint = Tint(200f, 0.025f), extras = LookExtras(grain = 0.12f)
    )
  )

  private val byId: Map<String, LookSpec> = looks.associateBy { it.id }

  fun find(id: String?): LookSpec? = if (id == null || id == NONE) null else byId[id]
}
