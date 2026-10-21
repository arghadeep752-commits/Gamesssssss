package com.devdarshan.nativemodule

import android.content.Context
import expo.modules.kotlin.Promise
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * JavaScript entry point (see packages/native/src/index.ts).
 *
 * File and network work runs on a small dedicated pool so a long download never
 * blocks other calls such as cancelDownload. UI work (share sheet, Google account
 * picker) runs on the main thread.
 */
class DevDarshanNativeModule : Module() {
  private val io: ExecutorService by lazy { Executors.newFixedThreadPool(3) }
  private var imageCache: ImageCache? = null

  private fun cacheFor(context: Context): ImageCache =
    imageCache ?: ImageCache(context.applicationContext).also { imageCache = it }

  override fun definition() = ModuleDefinition {
    Name("DevDarshanNative")

    Events("onDownloadProgress")

    AsyncFunction("getCapabilities") { promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) {
        WallpaperSetter(context).capabilities() + mapOf(
          "whatsappPackage" to ShareHelper(context).installedWhatsApp(),
          "needsStoragePermission" to GallerySaver(context).needsLegacyPermission(),
        )
      }
    }

    AsyncFunction("downloadOriginal") { key: String, url: String, promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) {
        val cache = cacheFor(context)
        val image = cache.find(key) ?: cache.download(key, url) { written, total ->
          sendEvent(
            "onDownloadProgress",
            mapOf("key" to key, "bytesWritten" to written.toDouble(), "totalBytes" to total.toDouble()),
          )
        }
        image.toMap()
      }
    }

    AsyncFunction("getCachedOriginal") { key: String, promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) { cacheFor(context).find(key)?.toMap() }
    }

    Function("cancelDownload") { key: String ->
      imageCache?.cancel(key)
    }

    AsyncFunction("setWallpaper") { path: String, target: String, promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) { WallpaperSetter(context).set(File(path), target) }
    }

    AsyncFunction("saveToGallery") { path: String, displayName: String, mimeType: String, promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) { GallerySaver(context).save(File(path), displayName, mimeType) }
    }

    AsyncFunction("shareImage") { path: String, mimeType: String, target: String, text: String?, chooserTitle: String?, promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      val helper = ShareHelper(context)
      io.execute {
        try {
          val shareFile = helper.prepare(File(path))
          val activity = appContext.currentActivity
          if (activity == null) {
            promise.reject(ErrorCodes.NO_ACTIVITY, "The app is not in the foreground", null)
            return@execute
          }
          activity.runOnUiThread {
            try {
              promise.resolve(helper.launch(activity, shareFile, mimeType, target, text, chooserTitle))
            } catch (e: NativeError) {
              promise.reject(e.code, e.message, e)
            } catch (e: Throwable) {
              promise.reject(ErrorCodes.SHARE_FAILED, e.message ?: "Could not open sharing", e)
            }
          }
        } catch (e: NativeError) {
          promise.reject(e.code, e.message, e)
        } catch (e: Throwable) {
          promise.reject(ErrorCodes.SHARE_FAILED, e.message ?: "Could not prepare the image for sharing", e)
        }
      }
    }

    AsyncFunction("googleSignIn") { webClientId: String, promise: Promise ->
      val activity = appContext.currentActivity
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_ACTIVITY, "The app is not in the foreground", null)
      activity.runOnUiThread { GoogleSignInHelper.signIn(activity, webClientId, promise) }
    }

    AsyncFunction("googleSignOut") { promise: Promise ->
      val context = appContext.reactContext ?: return@AsyncFunction promise.resolve(null)
      GoogleSignInHelper.signOut(context, promise)
    }

    // Test builds only: a generated image for the on-device self-test.
    AsyncFunction("createSelfTestImage") { promise: Promise ->
      val context = appContext.reactContext
        ?: return@AsyncFunction promise.reject(ErrorCodes.NO_CONTEXT, "App context unavailable", null)
      runIo(promise) { SelfTestImage.create(context) }
    }

    AsyncFunction("getCacheSize") { promise: Promise ->
      val context = appContext.reactContext ?: return@AsyncFunction promise.resolve(0.0)
      runIo(promise) { cacheFor(context).size().toDouble() }
    }

    AsyncFunction("clearCache") { promise: Promise ->
      val context = appContext.reactContext ?: return@AsyncFunction promise.resolve(0.0)
      runIo(promise) { cacheFor(context).clear().toDouble() }
    }

    OnDestroy {
      io.shutdownNow()
    }
  }

  private fun runIo(promise: Promise, block: () -> Any?) {
    io.execute {
      try {
        promise.resolve(block())
      } catch (e: NativeError) {
        promise.reject(e.code, e.message, e)
      } catch (e: Throwable) {
        promise.reject(ErrorCodes.UNKNOWN, e.message ?: e.javaClass.simpleName, e)
      }
    }
  }
}
