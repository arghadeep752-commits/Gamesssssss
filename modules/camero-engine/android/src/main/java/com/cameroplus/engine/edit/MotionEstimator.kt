package com.cameroplus.engine.edit

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Image-based motion estimation on small 8-bit luma frames. Used for live and post-recording
 * stabilization (no gyroscope needed) and for motion-compensated frame interpolation.
 */
object MotionEstimator {
  /** Global motion from previous to current frame, in pixels of the analysed frame. */
  class Motion(val dx: Float, val dy: Float, val angle: Float, val scale: Float, val confidence: Float) {
    companion object {
      val NONE = Motion(0f, 0f, 0f, 0f, 0f)
    }
  }

  /** Extracts luma from an RGBA buffer (row-major, tightly packed). */
  fun lumaFromRgba(rgba: ByteArray, w: Int, h: Int, out: ByteArray) {
    var j = 0
    for (i in 0 until w * h) {
      val r = rgba[j].toInt() and 0xFF
      val g = rgba[j + 1].toInt() and 0xFF
      val b = rgba[j + 2].toInt() and 0xFF
      out[i] = ((77 * r + 150 * g + 29 * b) shr 8).toByte()
      j += 4
    }
  }

  private fun sad(prev: ByteArray, cur: ByteArray, w: Int, x0: Int, y0: Int, dx: Int, dy: Int, size: Int, best: Int): Int {
    var sum = 0
    for (y in 0 until size) {
      var ci = (y0 + y) * w + x0
      var pi = (y0 + y - dy) * w + x0 - dx
      for (x in 0 until size) {
        sum += abs((cur[ci].toInt() and 0xFF) - (prev[pi].toInt() and 0xFF))
        ci++
        pi++
      }
      if (sum >= best) return sum
    }
    return sum
  }

  private fun variance(img: ByteArray, w: Int, x0: Int, y0: Int, size: Int): Float {
    var s = 0L
    var s2 = 0L
    for (y in 0 until size) {
      var i = (y0 + y) * w + x0
      for (x in 0 until size) {
        val v = img[i].toInt() and 0xFF
        s += v
        s2 += v * v
        i++
      }
    }
    val n = (size * size).toFloat()
    val mean = s / n
    return s2 / n - mean * mean
  }

  /**
   * Best displacement of the block at (x0, y0) in [cur] relative to [prev], searching around
   * (cx, cy) within +-[range]. Returns (dx, dy, sad) with sub-pixel refinement.
   */
  fun matchBlock(
    prev: ByteArray, cur: ByteArray, w: Int, h: Int,
    x0: Int, y0: Int, size: Int, cx: Int, cy: Int, range: Int, out: FloatArray
  ) {
    var best = Int.MAX_VALUE
    var bx = cx
    var by = cy
    for (dy in cy - range..cy + range) {
      if (y0 - dy < 0 || y0 - dy + size > h) continue
      for (dx in cx - range..cx + range) {
        if (x0 - dx < 0 || x0 - dx + size > w) continue
        val s = sad(prev, cur, w, x0, y0, dx, dy, size, best)
        if (s < best) {
          best = s; bx = dx; by = dy
        }
      }
    }
    var fx = bx.toFloat()
    var fy = by.toFloat()
    if (best != Int.MAX_VALUE) {
      fun cost(dx: Int, dy: Int): Int =
        if (y0 - dy < 0 || y0 - dy + size > h || x0 - dx < 0 || x0 - dx + size > w) -1
        else sad(prev, cur, w, x0, y0, dx, dy, size, Int.MAX_VALUE)
      val l = cost(bx - 1, by)
      val r = cost(bx + 1, by)
      if (l >= 0 && r >= 0) {
        val denom = (l - 2 * best + r).toFloat()
        if (denom > 0f) fx += ((l - r) / (2f * denom)).coerceIn(-0.5f, 0.5f)
      }
      val u = cost(bx, by - 1)
      val d = cost(bx, by + 1)
      if (u >= 0 && d >= 0) {
        val denom = (u - 2 * best + d).toFloat()
        if (denom > 0f) fy += ((u - d) / (2f * denom)).coerceIn(-0.5f, 0.5f)
      }
    }
    out[0] = fx
    out[1] = fy
    out[2] = if (best == Int.MAX_VALUE) -1f else best.toFloat()
  }

  /** Robust similarity motion (translation, rotation, scale) between two frames. */
  fun globalMotion(prev: ByteArray, cur: ByteArray, w: Int, h: Int, range: Int = 7): Motion {
    val size = max(8, min(w, h) / 8)
    val gx = 8
    val gy = 5
    val margin = range + 1
    val usableW = w - 2 * margin - size
    val usableH = h - 2 * margin - size
    if (usableW <= 0 || usableH <= 0) return Motion.NONE
    val xs = ArrayList<Float>()
    val ys = ArrayList<Float>()
    val dxs = ArrayList<Float>()
    val dys = ArrayList<Float>()
    val tmp = FloatArray(3)
    for (j in 0 until gy) {
      for (i in 0 until gx) {
        val x0 = margin + usableW * i / (gx - 1)
        val y0 = margin + usableH * j / (gy - 1)
        if (variance(cur, w, x0, y0, size) < 18f) continue
        matchBlock(prev, cur, w, h, x0, y0, size, 0, 0, range, tmp)
        if (tmp[2] < 0f) continue
        xs.add(x0 + size / 2f - w / 2f)
        ys.add(y0 + size / 2f - h / 2f)
        dxs.add(tmp[0])
        dys.add(tmp[1])
      }
    }
    if (xs.size < 4) return Motion.NONE
    var inliers = BooleanArray(xs.size) { true }
    var params = fitSimilarity(xs, ys, dxs, dys, inliers) ?: return Motion.NONE
    repeat(2) {
      val residuals = FloatArray(xs.size) { k -> residual(params, xs[k], ys[k], dxs[k], dys[k]) }
      val sorted = residuals.sorted()
      val median = sorted[sorted.size / 2]
      val limit = max(1.2f, median * 2.5f)
      inliers = BooleanArray(xs.size) { k -> residuals[k] <= limit }
      if (inliers.count { it } >= 4) params = fitSimilarity(xs, ys, dxs, dys, inliers) ?: params
    }
    val confidence = inliers.count { it }.toFloat() / (gx * gy)
    return Motion(params[0], params[1], params[2], params[3], confidence)
  }

  private fun residual(p: FloatArray, x: Float, y: Float, dx: Float, dy: Float): Float {
    val ex = p[0] - p[2] * y + p[3] * x - dx
    val ey = p[1] + p[2] * x + p[3] * y - dy
    return sqrt(ex * ex + ey * ey)
  }

  /**
   * Least squares for dx = tx - a*y + s*x, dy = ty + a*x + s*y with centred coordinates.
   * Returns [tx, ty, angle, scaleDelta].
   */
  private fun fitSimilarity(xs: List<Float>, ys: List<Float>, dxs: List<Float>, dys: List<Float>, use: BooleanArray): FloatArray? {
    var n = 0.0
    var sx = 0.0; var sy = 0.0; var sdx = 0.0; var sdy = 0.0
    for (k in xs.indices) {
      if (!use[k]) continue
      n++; sx += xs[k]; sy += ys[k]; sdx += dxs[k]; sdy += dys[k]
    }
    if (n < 3) return null
    val mx = sx / n; val my = sy / n
    var srr = 0.0; var sa = 0.0; var ss = 0.0
    for (k in xs.indices) {
      if (!use[k]) continue
      val x = xs[k] - mx
      val y = ys[k] - my
      val dx = dxs[k] - sdx / n
      val dy = dys[k] - sdy / n
      srr += x * x + y * y
      sa += x * dy - y * dx
      ss += x * dx + y * dy
    }
    val angle = if (srr > 1e-6) sa / srr else 0.0
    val scale = if (srr > 1e-6) ss / srr else 0.0
    val tx = sdx / n - (-angle * my + scale * mx)
    val ty = sdy / n - (angle * mx + scale * my)
    return floatArrayOf(tx.toFloat(), ty.toFloat(), angle.toFloat(), scale.toFloat())
  }

  /** Halves a luma image (2x2 box filter). */
  fun downsample(src: ByteArray, w: Int, h: Int): ByteArray {
    val ow = w / 2
    val oh = h / 2
    val out = ByteArray(ow * oh)
    for (y in 0 until oh) {
      for (x in 0 until ow) {
        val i = (y * 2) * w + x * 2
        val s = (src[i].toInt() and 0xFF) + (src[i + 1].toInt() and 0xFF) +
          (src[i + w].toInt() and 0xFF) + (src[i + w + 1].toInt() and 0xFF)
        out[y * ow + x] = (s shr 2).toByte()
      }
    }
    return out
  }

  /**
   * Dense block motion field (coarse-to-fine) for frame interpolation.
   * Returns [cols * rows * 2] displacements in pixels of the analysed frame (prev -> cur).
   */
  fun blockField(prev: ByteArray, cur: ByteArray, w: Int, h: Int, block: Int, cols: Int, rows: Int): FloatArray {
    val field = FloatArray(cols * rows * 2)
    val pw = w / 2
    val ph = h / 2
    val prevS = downsample(prev, w, h)
    val curS = downsample(cur, w, h)
    val half = max(4, block / 2)
    val tmp = FloatArray(3)
    for (j in 0 until rows) {
      for (i in 0 until cols) {
        val cx = (i + 0.5f) * w / cols
        val cy = (j + 0.5f) * h / rows
        // coarse
        val sx0 = ((cx / 2f) - half / 2f).toInt().coerceIn(0, pw - half)
        val sy0 = ((cy / 2f) - half / 2f).toInt().coerceIn(0, ph - half)
        matchBlock(prevS, curS, pw, ph, sx0, sy0, half, 0, 0, 5, tmp)
        val gx = if (tmp[2] < 0f) 0 else Math.round(tmp[0] * 2)
        val gy = if (tmp[2] < 0f) 0 else Math.round(tmp[1] * 2)
        // fine
        val x0 = (cx - block / 2f).toInt().coerceIn(0, w - block)
        val y0 = (cy - block / 2f).toInt().coerceIn(0, h - block)
        matchBlock(prev, cur, w, h, x0, y0, block, gx, gy, 2, tmp)
        val idx = (j * cols + i) * 2
        if (tmp[2] < 0f) {
          field[idx] = gx.toFloat(); field[idx + 1] = gy.toFloat()
        } else {
          field[idx] = tmp[0]; field[idx + 1] = tmp[1]
        }
      }
    }
    return median3x3(field, cols, rows)
  }

  private fun median3x3(field: FloatArray, cols: Int, rows: Int): FloatArray {
    val out = FloatArray(field.size)
    val bx = FloatArray(9)
    val by = FloatArray(9)
    for (j in 0 until rows) {
      for (i in 0 until cols) {
        var n = 0
        for (dj in -1..1) for (di in -1..1) {
          val x = (i + di).coerceIn(0, cols - 1)
          val y = (j + dj).coerceIn(0, rows - 1)
          bx[n] = field[(y * cols + x) * 2]
          by[n] = field[(y * cols + x) * 2 + 1]
          n++
        }
        bx.sort(); by.sort()
        out[(j * cols + i) * 2] = bx[4]
        out[(j * cols + i) * 2 + 1] = by[4]
      }
    }
    return out
  }
}
