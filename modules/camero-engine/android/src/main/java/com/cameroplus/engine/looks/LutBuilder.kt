package com.cameroplus.engine.looks

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cbrt
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Bakes a [LookSpec] into an N x N x N LUT laid out as an (N*N) x N RGBA strip:
 * blue selects the slice, red runs along x inside a slice, green along y.
 */
object LutBuilder {
  const val SIZE = 33

  fun build(spec: LookSpec, size: Int = SIZE): ByteBuffer {
    val prepared = Prepared(spec)
    val buffer = ByteBuffer.allocateDirect(size * size * size * 4).order(ByteOrder.nativeOrder())
    val out = FloatArray(3)
    val step = 1f / (size - 1)
    for (g in 0 until size) {
      for (b in 0 until size) {
        for (r in 0 until size) {
          prepared.apply(r * step, g * step, b * step, out)
          // row = g, column = b * size + r
          val index = (g * size * size + b * size + r) * 4
          buffer.put(index, toByte(out[0]))
          buffer.put(index + 1, toByte(out[1]))
          buffer.put(index + 2, toByte(out[2]))
          buffer.put(index + 3, 0xFF.toByte())
        }
      }
    }
    buffer.position(0)
    return buffer
  }

  /** Applies the look to one sRGB colour (0..1). Used for tone signatures and tests. */
  fun applyOne(spec: LookSpec, r: Float, g: Float, b: Float): FloatArray {
    val out = FloatArray(3)
    Prepared(spec).apply(r, g, b, out)
    return out
  }

  private fun toByte(v: Float): Byte = (v.coerceIn(0f, 1f) * 255f + 0.5f).toInt().toByte()

  fun srgbToLinear(v: Float): Float =
    if (v <= 0.04045f) v / 12.92f else ((v + 0.055f) / 1.055f).toDouble().pow(2.4).toFloat()

  fun linearToSrgb(v: Float): Float {
    val x = max(v, 0f)
    return if (x <= 0.0031308f) x * 12.92f else (1.055 * x.toDouble().pow(1.0 / 2.4) - 0.055).toFloat()
  }

  /** White balance gains shared with the shader path so both agree. */
  fun whiteBalance(temperature: Float, tint: Float): FloatArray {
    var r = 1f + 0.22f * temperature
    var g = 1f - 0.14f * tint
    var b = 1f - 0.22f * temperature
    val lum = 0.2126f * r + 0.7152f * g + 0.0722f * b
    r /= lum; g /= lum; b /= lum
    return floatArrayOf(r, g, b)
  }

  private class Prepared(val s: LookSpec) {
    val exposureGain = 2.0.pow(s.exposure.toDouble()).toFloat()
    val wb = whiteBalance(s.temperature, s.tint)
    val shoulderKnee = 1f - 0.55f * s.shoulder
    val shoulderQ = solveShoulder(1f - 0.25f * s.shoulder)
    val contrastGamma = exp(s.contrast * 0.9f)
    val pivotExp = (ln(0.5) / ln(s.pivot.coerceIn(0.2f, 0.8f).toDouble())).toFloat()
    val curveRgb = s.curveRgb?.let { MonotoneCurve(it) }
    val curveR = s.curveR?.let { MonotoneCurve(it) }
    val curveG = s.curveG?.let { MonotoneCurve(it) }
    val curveB = s.curveB?.let { MonotoneCurve(it) }
    val lab = FloatArray(3)
    val rgb = FloatArray(3)

    fun apply(r0: Float, g0: Float, b0: Float, out: FloatArray) {
      // 1. Linear light: exposure, white balance, channel mixer.
      var r = srgbToLinear(r0) * exposureGain * wb[0]
      var g = srgbToLinear(g0) * exposureGain * wb[1]
      var b = srgbToLinear(b0) * exposureGain * wb[2]
      s.mixer?.let { m ->
        val nr = m[0] * r + m[1] * g + m[2] * b
        val ng = m[3] * r + m[4] * g + m[5] * b
        val nb = m[6] * r + m[7] * g + m[8] * b
        r = nr; g = ng; b = nb
      }

      // 2. Display-referred tone: shoulder, pivoted filmic contrast, curves.
      rgb[0] = tone(linearToSrgb(r))
      rgb[1] = tone(linearToSrgb(g))
      rgb[2] = tone(linearToSrgb(b))
      curveRgb?.let { c -> for (i in 0..2) rgb[i] = c.eval(rgb[i]) }
      curveR?.let { rgb[0] = it.eval(rgb[0]) }
      curveG?.let { rgb[1] = it.eval(rgb[1]) }
      curveB?.let { rgb[2] = it.eval(rgb[2]) }

      // 3. Colour in OkLCh: saturation, vibrance, hue bands, split toning.
      linearToOklab(srgbToLinear(rgb[0]), srgbToLinear(rgb[1]), srgbToLinear(rgb[2]), lab)
      var L = lab[0]
      var A = lab[1]
      var B = lab[2]
      var C = sqrt(A * A + B * B)
      var h = Math.toDegrees(atan2(B.toDouble(), A.toDouble())).toFloat()
      if (h < 0f) h += 360f

      val chromaGate = smooth(0.012f, 0.045f, C)
      val skin = bandWeight(h, 55f, 28f) * smooth(0.02f, 0.06f, C) * (1f - smooth(0.16f, 0.24f, C))
      val protect = skin * s.skinProtect

      var chromaScale = 1f + s.saturation * (1f - 0.5f * protect)
      chromaScale *= 1f + s.vibrance * (1f - smooth(0f, 0.2f, C)) * (1f - protect)
      chromaScale *= lerp(s.shadowSat, 1f, smooth(0.25f, 0.55f, L))
      chromaScale *= lerp(1f, s.highlightSat, smooth(0.7f, 0.95f, L))

      var hueShift = 0f
      var lumShift = 0f
      for (band in s.bands) {
        val w = bandWeight(h, band.hue, band.width) * chromaGate
        if (w <= 0f) continue
        val keep = if (band.shift != 0f) 1f - protect else 1f
        hueShift += band.shift * w * keep
        chromaScale *= 1f + (band.sat - 1f) * w
        lumShift += band.lum * w
      }
      C *= max(chromaScale, 0f)
      h += hueShift
      L += lumShift
      val hr = Math.toRadians(h.toDouble())
      A = (C * cos(hr)).toFloat()
      B = (C * sin(hr)).toFloat()

      val balance = s.splitBalance * 0.2f
      s.shadowTint?.let { t ->
        val w = 1f - smooth(0.2f, 0.62f, L + balance)
        val tr = Math.toRadians(t.hue.toDouble())
        A += (cos(tr) * t.amount * w).toFloat()
        B += (sin(tr) * t.amount * w).toFloat()
      }
      s.highlightTint?.let { t ->
        val w = smooth(0.5f, 0.95f, L + balance)
        val tr = Math.toRadians(t.hue.toDouble())
        A += (cos(tr) * t.amount * w).toFloat()
        B += (sin(tr) * t.amount * w).toFloat()
      }
      oklabToLinear(L, A, B, rgb)

      // 4. Output range (fade / matte) and encode.
      val lift = s.blackLift
      val top = s.whitePoint
      for (i in 0..2) {
        val v = linearToSrgb(rgb[i]).coerceIn(0f, 1f)
        out[i] = (lift + v * (top - lift)).coerceIn(0f, 1f)
      }
    }

    private fun tone(v0: Float): Float {
      var v = v0
      if (s.shoulder > 0f && v > shoulderKnee) {
        val x = (v - shoulderKnee) / (1f - shoulderKnee)
        val y = if (shoulderQ < 1e-4f) x else ((1f - exp(-x * shoulderQ)) / shoulderQ)
        v = shoulderKnee + (1f - shoulderKnee) * y
      }
      v = v.coerceIn(0f, 1f)
      if (abs(s.contrast) > 1e-4f) {
        val u = v.toDouble().pow(pivotExp.toDouble()).toFloat()
        val a = u.toDouble().pow(contrastGamma.toDouble())
        val bb = (1f - u).toDouble().pow(contrastGamma.toDouble())
        val f = (a / max(a + bb, 1e-9)).toFloat()
        v = f.toDouble().pow(1.0 / pivotExp).toFloat()
      }
      return v
    }
  }

  /** Finds q so that (1 - e^-q) / q equals [target]; q = 0 means no compression. */
  private fun solveShoulder(target: Float): Float {
    if (target >= 0.9999f) return 0f
    var lo = 1e-4
    var hi = 20.0
    repeat(60) {
      val mid = (lo + hi) / 2
      val value = (1 - exp(-mid)) / mid
      if (value > target) lo = mid else hi = mid
    }
    return ((lo + hi) / 2).toFloat()
  }

  private fun smooth(e0: Float, e1: Float, x: Float): Float {
    val t = ((x - e0) / (e1 - e0)).coerceIn(0f, 1f)
    return t * t * (3f - 2f * t)
  }

  private fun lerp(a: Float, b: Float, t: Float) = a + (b - a) * t

  private fun bandWeight(h: Float, center: Float, width: Float): Float {
    var d = abs(h - center) % 360f
    if (d > 180f) d = 360f - d
    if (d >= width) return 0f
    return (0.5 * (1 + cos(PI * d / width))).toFloat()
  }

  fun linearToOklab(r: Float, g: Float, b: Float, out: FloatArray) {
    val l = cbrt(0.4122214708f * r + 0.5363325363f * g + 0.0514459929f * b)
    val m = cbrt(0.2119034982f * r + 0.6806995451f * g + 0.1073969566f * b)
    val s = cbrt(0.0883024619f * r + 0.2817188376f * g + 0.6299787005f * b)
    out[0] = 0.2104542553f * l + 0.7936177850f * m - 0.0040720468f * s
    out[1] = 1.9779984951f * l - 2.4285922050f * m + 0.4505937099f * s
    out[2] = 0.0259040371f * l + 0.7827717662f * m - 0.8086757660f * s
  }

  fun oklabToLinear(L: Float, a: Float, b: Float, out: FloatArray) {
    val l1 = L + 0.3963377774f * a + 0.2158037573f * b
    val m1 = L - 0.1055613458f * a - 0.0638541728f * b
    val s1 = L - 0.0894841775f * a - 1.2914855480f * b
    val l = l1 * l1 * l1
    val m = m1 * m1 * m1
    val s = s1 * s1 * s1
    out[0] = (4.0767416621f * l - 3.3077115913f * m + 0.2309699292f * s).coerceIn(0f, 1f)
    out[1] = (-1.2684380046f * l + 2.6097574011f * m - 0.3413193965f * s).coerceIn(0f, 1f)
    out[2] = (-0.0041960863f * l - 0.7034186147f * m + 1.7076147010f * s).coerceIn(0f, 1f)
  }

  /** Fritsch-Carlson monotone cubic through (x, y) pairs. */
  class MonotoneCurve(points: FloatArray) {
    private val xs: FloatArray
    private val ys: FloatArray
    private val ms: FloatArray

    init {
      val n = points.size / 2
      xs = FloatArray(n) { points[it * 2] }
      ys = FloatArray(n) { points[it * 2 + 1] }
      val d = FloatArray(max(n - 1, 1)) { i ->
        if (i < n - 1) (ys[i + 1] - ys[i]) / max(xs[i + 1] - xs[i], 1e-6f) else 0f
      }
      ms = FloatArray(n)
      if (n >= 2) {
        ms[0] = d[0]
        ms[n - 1] = d[n - 2]
        for (i in 1 until n - 1) {
          ms[i] = if (d[i - 1] * d[i] <= 0f) 0f else (d[i - 1] + d[i]) / 2f
        }
        for (i in 0 until n - 1) {
          if (abs(d[i]) < 1e-6f) {
            ms[i] = 0f; ms[i + 1] = 0f
          } else {
            val a = ms[i] / d[i]
            val b = ms[i + 1] / d[i]
            val t = a * a + b * b
            if (t > 9f) {
              val k = 3f / sqrt(t)
              ms[i] = k * a * d[i]
              ms[i + 1] = k * b * d[i]
            }
          }
        }
      }
    }

    fun eval(x: Float): Float {
      val n = xs.size
      if (n == 0) return x
      if (x <= xs[0]) return ys[0]
      if (x >= xs[n - 1]) return ys[n - 1]
      var i = 0
      while (i < n - 2 && x > xs[i + 1]) i++
      val h = xs[i + 1] - xs[i]
      val t = (x - xs[i]) / h
      val t2 = t * t
      val t3 = t2 * t
      val h00 = 2 * t3 - 3 * t2 + 1
      val h10 = t3 - 2 * t2 + t
      val h01 = -2 * t3 + 3 * t2
      val h11 = t3 - t2
      return (h00 * ys[i] + h10 * h * ms[i] + h01 * ys[i + 1] + h11 * h * ms[i + 1]).coerceIn(0f, 1f)
    }
  }

  @Suppress("unused")
  private fun clamp01(v: Float) = min(max(v, 0f), 1f)
}
