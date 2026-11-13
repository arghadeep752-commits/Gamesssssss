package com.cameroplus.engine.edit

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.BitmapRegionDecoder
import android.graphics.Canvas
import android.graphics.Rect
import android.net.Uri
import android.opengl.GLES20
import android.opengl.GLUtils
import android.os.Build
import androidx.exifinterface.media.ExifInterface
import com.cameroplus.engine.gl.Affine
import com.cameroplus.engine.gl.DrawFrame
import com.cameroplus.engine.gl.EditTransform
import com.cameroplus.engine.gl.GlCore
import com.cameroplus.engine.gl.GradeProgram
import com.cameroplus.engine.gl.LutTexture
import com.cameroplus.engine.looks.GradeParams
import com.cameroplus.engine.looks.LookLibrary
import com.cameroplus.engine.looks.LutCache
import com.cameroplus.engine.media.MediaProbe
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Renders photos through the grading shader at full resolution. The source is decoded tile by tile
 * with BitmapRegionDecoder so large images never sit in memory twice; the GPU does the colour work.
 */
object PhotoRenderer {
  private const val TILE = 1024

  private val EXIF_TAGS = listOf(
    ExifInterface.TAG_DATETIME, ExifInterface.TAG_DATETIME_ORIGINAL, ExifInterface.TAG_DATETIME_DIGITIZED,
    ExifInterface.TAG_OFFSET_TIME, ExifInterface.TAG_OFFSET_TIME_ORIGINAL, ExifInterface.TAG_OFFSET_TIME_DIGITIZED,
    ExifInterface.TAG_SUBSEC_TIME, ExifInterface.TAG_SUBSEC_TIME_ORIGINAL, ExifInterface.TAG_SUBSEC_TIME_DIGITIZED,
    ExifInterface.TAG_MAKE, ExifInterface.TAG_MODEL, ExifInterface.TAG_LENS_MAKE, ExifInterface.TAG_LENS_MODEL,
    ExifInterface.TAG_EXPOSURE_TIME, ExifInterface.TAG_F_NUMBER, ExifInterface.TAG_APERTURE_VALUE,
    ExifInterface.TAG_SHUTTER_SPEED_VALUE, ExifInterface.TAG_EXPOSURE_BIAS_VALUE, ExifInterface.TAG_EXPOSURE_PROGRAM,
    ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY, ExifInterface.TAG_FOCAL_LENGTH, ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM,
    ExifInterface.TAG_WHITE_BALANCE, ExifInterface.TAG_FLASH, ExifInterface.TAG_METERING_MODE,
    ExifInterface.TAG_GPS_LATITUDE, ExifInterface.TAG_GPS_LATITUDE_REF, ExifInterface.TAG_GPS_LONGITUDE,
    ExifInterface.TAG_GPS_LONGITUDE_REF, ExifInterface.TAG_GPS_ALTITUDE, ExifInterface.TAG_GPS_ALTITUDE_REF,
    ExifInterface.TAG_GPS_TIMESTAMP, ExifInterface.TAG_GPS_DATESTAMP
  )

  /**
   * Renders [source] with [grade] and [transform] into [output]. Returns the output size.
   * [format] is "jpeg" or "png". Throws on failure; the source is never modified.
   */
  fun render(
    context: Context,
    source: Uri,
    output: File,
    grade: GradeParams,
    transform: EditTransform,
    format: String,
    quality: Int
  ): IntArray {
    val orientation = MediaProbe.exifOrientation(context, source)
    val pfd = context.contentResolver.openFileDescriptor(source, "r") ?: throw IOException("Can't open the photo")
    pfd.use { descriptor ->
      val decoder = if (Build.VERSION.SDK_INT >= 31) {
        BitmapRegionDecoder.newInstance(descriptor.fileDescriptor)
      } else {
        @Suppress("DEPRECATION")
        BitmapRegionDecoder.newInstance(descriptor.fileDescriptor, false)
      } ?: throw IOException("Unsupported photo format")
      try {
        val sw = decoder.width
        val sh = decoder.height
        val swap = Affine.exifSwapsAxes(orientation)
        val dw = if (swap) sh else sw
        val dh = if (swap) sw else sh
        val outSize = transform.outputSize(dw, dh)
        val ow = outSize[0]
        val oh = outSize[1]
        val toStored = Affine.exifDisplayedToStored(orientation) * transform.outputToDisplayed()
        val bitmap = renderTiles(decoder, sw, sh, ow, oh, toStored, grade)
        try {
          FileOutputStream(output).use { out ->
            if (format == "png") bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            else bitmap.compress(Bitmap.CompressFormat.JPEG, quality.coerceIn(50, 100), out)
          }
        } finally {
          bitmap.recycle()
        }
        if (format != "png") copyExif(context, source, output, ow, oh)
        return intArrayOf(ow, oh)
      } finally {
        decoder.recycle()
      }
    }
  }

  private fun renderTiles(
    decoder: BitmapRegionDecoder,
    sw: Int, sh: Int, ow: Int, oh: Int,
    toStored: Affine,
    grade: GradeParams
  ): Bitmap {
    val out = try {
      Bitmap.createBitmap(ow, oh, Bitmap.Config.ARGB_8888)
    } catch (e: OutOfMemoryError) {
      throw IOException("Not enough memory to render ${ow}x$oh at full resolution")
    }
    val canvas = Canvas(out)
    val uniforms = grade.uniforms()
    val core = GlCore(recordable = false)
    try {
      val program = GradeProgram(external = false)
      val lut = LutTexture()
      uniforms.lutKey?.let { key -> LutCache.get(key)?.let { lut.upload(key, uniforms.lutSize, it) } }
      val tile = min(TILE, GlCore.maxTextureSize() / 2)
      val pad = if (uniforms.needsNeighbourhood) {
        (ceil(max(sw, sh) * 0.004f * 1.8f).toInt() + 4).coerceAtMost(96)
      } else 1
      val fboTex = GlCore.create2dTexture()
      GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, tile, tile, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
      val fbo = IntArray(1)
      GLES20.glGenFramebuffers(1, fbo, 0)
      GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo[0])
      GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, fboTex, 0)
      if (GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER) != GLES20.GL_FRAMEBUFFER_COMPLETE) {
        throw IOException("GPU framebuffer unavailable")
      }
      val srcTex = GlCore.create2dTexture()
      val pixels = ByteBuffer.allocateDirect(tile * tile * 4).order(ByteOrder.nativeOrder())
      val opts = BitmapFactory.Options().apply { inPreferredConfig = Bitmap.Config.ARGB_8888 }
      var y0 = 0
      while (y0 < oh) {
        val th = min(tile, oh - y0)
        var x0 = 0
        while (x0 < ow) {
          val tw = min(tile, ow - x0)
          val tileToGlobal = Affine(
            a = tw.toFloat() / ow, d = th.toFloat() / oh,
            e = x0.toFloat() / ow, f = y0.toFloat() / oh
          )
          val toStoredTile = toStored * tileToGlobal
          var minX = Float.MAX_VALUE; var minY = Float.MAX_VALUE
          var maxX = -Float.MAX_VALUE; var maxY = -Float.MAX_VALUE
          for ((u, v) in listOf(0f to 0f, 1f to 0f, 0f to 1f, 1f to 1f)) {
            val x = toStoredTile.mapX(u, v) * sw
            val y = toStoredTile.mapY(u, v) * sh
            minX = min(minX, x); maxX = max(maxX, x)
            minY = min(minY, y); maxY = max(maxY, y)
          }
          val rx0 = (floor(minX).toInt() - pad).coerceIn(0, sw - 1)
          val ry0 = (floor(minY).toInt() - pad).coerceIn(0, sh - 1)
          val rx1 = (ceil(maxX).toInt() + pad).coerceIn(rx0 + 1, sw)
          val ry1 = (ceil(maxY).toInt() + pad).coerceIn(ry0 + 1, sh)
          val rw = rx1 - rx0
          val rh = ry1 - ry0
          val region = decoder.decodeRegion(Rect(rx0, ry0, rx1, ry1), opts)
            ?: throw IOException("Couldn't decode part of the photo")
          GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, srcTex)
          GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, region, 0)
          region.recycle()
          val storedToRegion = Affine(
            a = sw.toFloat() / rw, d = sh.toFloat() / rh,
            e = -rx0.toFloat() / rw, f = -ry0.toFloat() / rh
          )
          GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo[0])
          GLES20.glViewport(0, 0, tw, th)
          program.draw(
            srcTex,
            (storedToRegion * toStoredTile).toMat4(),
            tileToGlobal.toMat4(),
            uniforms,
            lut.texture,
            DrawFrame(ow, oh, 1f / rw, 1f / rh, max(sw, sh).toFloat(), seed = 11f)
          )
          pixels.position(0)
          GLES20.glReadPixels(0, 0, tw, th, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, pixels)
          pixels.position(0)
          pixels.limit(tw * th * 4)
          val tileBitmap = Bitmap.createBitmap(tw, th, Bitmap.Config.ARGB_8888)
          tileBitmap.copyPixelsFromBuffer(pixels)
          pixels.clear()
          canvas.drawBitmap(tileBitmap, x0.toFloat(), y0.toFloat(), null)
          tileBitmap.recycle()
          x0 += tile
        }
        y0 += tile
      }
      GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
      GLES20.glDeleteFramebuffers(1, fbo, 0)
      GlCore.deleteTexture(fboTex)
      GlCore.deleteTexture(srcTex)
      lut.release()
      program.release()
    } catch (e: Throwable) {
      out.recycle()
      throw e
    } finally {
      core.release()
    }
    return out
  }

  private fun copyExif(context: Context, source: Uri, output: File, width: Int, height: Int) {
    try {
      val src = context.contentResolver.openInputStream(source)?.use { ExifInterface(it) } ?: return
      val dst = ExifInterface(output.absolutePath)
      for (tag in EXIF_TAGS) src.getAttribute(tag)?.let { dst.setAttribute(tag, it) }
      dst.setAttribute(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL.toString())
      dst.setAttribute(ExifInterface.TAG_PIXEL_X_DIMENSION, width.toString())
      dst.setAttribute(ExifInterface.TAG_PIXEL_Y_DIMENSION, height.toString())
      dst.setAttribute(ExifInterface.TAG_SOFTWARE, "Camero Plus")
      dst.saveAttributes()
    } catch (_: Exception) {
    }
  }

  /** Small previews of each look rendered on a real photo, cached as JPEGs. */
  fun renderLookPreviews(context: Context, source: Uri, size: Int, lookIds: List<String>): Map<String, String> {
    val orientation = MediaProbe.exifOrientation(context, source)
    val bitmap = MediaProbe.decodeSampled(context, source, (size * 1.3f).roundToInt()) ?: throw IOException("Couldn't read the photo")
    val stored = MediaProbe.storedImageSize(context, source)
    val result = LinkedHashMap<String, String>()
    val dir = File(context.cacheDir, "looks").apply { mkdirs() }
    val swap = Affine.exifSwapsAxes(orientation)
    val dw = if (swap) bitmap.height else bitmap.width
    val dh = if (swap) bitmap.width else bitmap.height
    val scale = size.toFloat() / max(dw, dh)
    val ow = max(2, (dw * scale).roundToInt())
    val oh = max(2, (dh * scale).roundToInt())
    val core = GlCore(recordable = false)
    try {
      val program = GradeProgram(external = false)
      val lut = LutTexture()
      val srcTex = GlCore.create2dTexture()
      GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bitmap, 0)
      val fboTex = GlCore.create2dTexture()
      GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, ow, oh, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
      val fbo = IntArray(1)
      GLES20.glGenFramebuffers(1, fbo, 0)
      GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo[0])
      GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, fboTex, 0)
      val texMatrix = Affine.exifDisplayedToStored(orientation).toMat4()
      val pixels = ByteBuffer.allocateDirect(ow * oh * 4).order(ByteOrder.nativeOrder())
      val detailScale = if (stored[0] > 0) bitmap.width.toFloat() / stored[0] else 1f
      val key = source.toString().hashCode()
      for (id in lookIds) {
        val file = File(dir, "${key}_${size}_$id.jpg")
        if (file.exists()) {
          result[id] = Uri.fromFile(file).toString()
          continue
        }
        val params = GradeParams(look = if (LookLibrary.find(id) != null) id else LookLibrary.NONE, intensity = 1f)
        val uniforms = params.uniforms()
        val lutTex = uniforms.lutKey?.let { k -> LutCache.get(k)?.let { lut.upload(k, uniforms.lutSize, it); lut.texture } } ?: 0
        GLES20.glViewport(0, 0, ow, oh)
        program.draw(
          srcTex, texMatrix, Affine.IDENTITY.toMat4(), uniforms, lutTex,
          DrawFrame(ow, oh, 1f / bitmap.width, 1f / bitmap.height, max(stored[0], stored[1]).toFloat(), detailScale)
        )
        pixels.position(0)
        GLES20.glReadPixels(0, 0, ow, oh, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, pixels)
        pixels.position(0)
        val bmp = Bitmap.createBitmap(ow, oh, Bitmap.Config.ARGB_8888)
        bmp.copyPixelsFromBuffer(pixels)
        FileOutputStream(file).use { bmp.compress(Bitmap.CompressFormat.JPEG, 88, it) }
        bmp.recycle()
        result[id] = Uri.fromFile(file).toString()
      }
      GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
      GLES20.glDeleteFramebuffers(1, fbo, 0)
      GlCore.deleteTexture(fboTex)
      GlCore.deleteTexture(srcTex)
      lut.release()
      program.release()
    } finally {
      core.release()
      bitmap.recycle()
    }
    return result
  }
}
