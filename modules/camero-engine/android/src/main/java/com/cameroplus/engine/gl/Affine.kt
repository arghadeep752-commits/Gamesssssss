package com.cameroplus.engine.gl

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 2D affine map used for texture coordinate math:
 *   x' = a*x + c*y + e
 *   y' = b*x + d*y + f
 * `p * q` means "apply q first, then p".
 */
data class Affine(
  val a: Float = 1f,
  val b: Float = 0f,
  val c: Float = 0f,
  val d: Float = 1f,
  val e: Float = 0f,
  val f: Float = 0f
) {
  operator fun times(o: Affine): Affine = Affine(
    a = a * o.a + c * o.b,
    b = b * o.a + d * o.b,
    c = a * o.c + c * o.d,
    d = b * o.c + d * o.d,
    e = a * o.e + c * o.f + e,
    f = b * o.e + d * o.f + f
  )

  fun mapX(x: Float, y: Float): Float = a * x + c * y + e
  fun mapY(x: Float, y: Float): Float = b * x + d * y + f

  fun inverse(): Affine {
    val det = a * d - b * c
    if (abs(det) < 1e-12f) return IDENTITY
    val ia = d / det
    val ib = -b / det
    val ic = -c / det
    val id = a / det
    return Affine(ia, ib, ic, id, -(ia * e + ic * f), -(ib * e + id * f))
  }

  /** Column-major 4x4 matrix for GLSL `mat4` uniforms. */
  fun toMat4(): FloatArray = floatArrayOf(
    a, b, 0f, 0f,
    c, d, 0f, 0f,
    0f, 0f, 1f, 0f,
    e, f, 0f, 1f
  )

  companion object {
    val IDENTITY = Affine()
    /** y -> 1 - y (top-left origin <-> bottom-left origin). */
    val FLIP_Y = Affine(d = -1f, f = 1f)
    /** x -> 1 - x */
    val FLIP_X = Affine(a = -1f, e = 1f)

    fun translate(x: Float, y: Float) = Affine(e = x, f = y)
    fun scale(sx: Float, sy: Float) = Affine(a = sx, d = sy)
    fun rotate(radians: Float): Affine {
      val cs = kotlin.math.cos(radians)
      val sn = kotlin.math.sin(radians)
      return Affine(a = cs, b = sn, c = -sn, d = cs)
    }

    /**
     * Stabilising map in normalized coordinates of a [w] x [h] frame: zooms in by [zoom] about the
     * centre, rotates by [radians] and shifts by ([dx], [dy]) normalized units (output -> source).
     */
    fun stabilizer(w: Float, h: Float, zoom: Float, dx: Float, dy: Float, radians: Float): Affine {
      val toPx = scale(w, h)
      val toNorm = scale(1f / w, 1f / h)
      val center = translate(w / 2f, h / 2f)
      val uncenter = translate(-w / 2f, -h / 2f)
      val px = translate(dx * w, dy * h) * center * rotate(radians) * scale(1f / zoom, 1f / zoom) * uncenter
      return toNorm * px * toPx
    }

    /** Takes the 2D affine part of a column-major 4x4 matrix (e.g. SurfaceTexture transform). */
    fun fromMat4(m: FloatArray) = Affine(m[0], m[1], m[4], m[5], m[12], m[13])

    /**
     * Maps a point of an image rotated clockwise by [degrees] back to the unrotated image.
     * Coordinates are normalized with a top-left origin.
     */
    fun unrotate(degrees: Int): Affine = when (((degrees % 360) + 360) % 360) {
      90 -> Affine(a = 0f, b = -1f, c = 1f, d = 0f, e = 0f, f = 1f)
      180 -> Affine(a = -1f, b = 0f, c = 0f, d = -1f, e = 1f, f = 1f)
      270 -> Affine(a = 0f, b = 1f, c = -1f, d = 0f, e = 1f, f = 0f)
      else -> IDENTITY
    }

    /**
     * Maps displayed-image coordinates to stored-pixel coordinates for an EXIF orientation value.
     */
    fun exifDisplayedToStored(orientation: Int): Affine = when (orientation) {
      2 -> FLIP_X
      3 -> unrotate(180)
      4 -> FLIP_Y
      5 -> FLIP_X * unrotate(270)
      6 -> unrotate(90)
      7 -> FLIP_X * unrotate(90)
      8 -> unrotate(270)
      else -> IDENTITY
    }

    fun exifSwapsAxes(orientation: Int): Boolean = orientation in 5..8
  }
}

/**
 * User geometry edits: rotate clockwise in 90 degree steps, mirror, then crop.
 * The crop rectangle is normalized (0..1, top-left origin) in the rotated and mirrored frame.
 */
data class EditTransform(
  val rotation: Int = 0,
  val flipH: Boolean = false,
  val flipV: Boolean = false,
  val cropX: Float = 0f,
  val cropY: Float = 0f,
  val cropW: Float = 1f,
  val cropH: Float = 1f
) {
  val isIdentity: Boolean
    get() = rotation % 360 == 0 && !flipH && !flipV &&
      abs(cropX) < 1e-4f && abs(cropY) < 1e-4f && abs(cropW - 1f) < 1e-4f && abs(cropH - 1f) < 1e-4f

  /** Output (top-left normalized) -> displayed source image (top-left normalized). */
  fun outputToDisplayed(ignoreCrop: Boolean = false): Affine {
    var m = if (ignoreCrop) Affine.IDENTITY else Affine(a = cropW, d = cropH, e = cropX, f = cropY)
    if (flipH) m = Affine.FLIP_X * m
    if (flipV) m = Affine.FLIP_Y * m
    return Affine.unrotate(rotation) * m
  }

  fun rotatedSize(width: Int, height: Int): IntArray {
    val r = ((rotation % 360) + 360) % 360
    return if (r == 90 || r == 270) intArrayOf(height, width) else intArrayOf(width, height)
  }

  /** Output pixel size for a displayed image of [width] x [height]. Always even and at least 2. */
  fun outputSize(width: Int, height: Int, ignoreCrop: Boolean = false): IntArray {
    val rs = rotatedSize(width, height)
    val w = if (ignoreCrop) rs[0].toFloat() else rs[0] * cropW
    val h = if (ignoreCrop) rs[1].toFloat() else rs[1] * cropH
    return intArrayOf(max(2, (w.roundToInt() / 2) * 2), max(2, (h.roundToInt() / 2) * 2))
  }

  companion object {
    fun fromJson(json: String?): EditTransform {
      if (json.isNullOrBlank()) return EditTransform()
      return try {
        val o = org.json.JSONObject(json)
        val crop = o.optJSONObject("crop")
        val cx = crop?.optDouble("x", 0.0)?.toFloat() ?: 0f
        val cy = crop?.optDouble("y", 0.0)?.toFloat() ?: 0f
        val cw = crop?.optDouble("w", 1.0)?.toFloat() ?: 1f
        val ch = crop?.optDouble("h", 1.0)?.toFloat() ?: 1f
        EditTransform(
          rotation = o.optInt("rotation", 0),
          flipH = o.optBoolean("flipH", false),
          flipV = o.optBoolean("flipV", false),
          cropX = cx.coerceIn(0f, 1f),
          cropY = cy.coerceIn(0f, 1f),
          cropW = min(max(cw, 0.02f), 1f - cx.coerceIn(0f, 1f)),
          cropH = min(max(ch, 0.02f), 1f - cy.coerceIn(0f, 1f))
        )
      } catch (e: Exception) {
        EditTransform()
      }
    }
  }
}
