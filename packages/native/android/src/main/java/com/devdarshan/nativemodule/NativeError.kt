package com.devdarshan.nativemodule

/** An error with a stable code; the JavaScript layer turns codes into user-facing messages. */
class NativeError(val code: String, message: String, cause: Throwable? = null) : Exception(message, cause)

object ErrorCodes {
  const val NETWORK = "E_NETWORK"
  const val HTTP = "E_HTTP"
  const val CANCELLED = "E_CANCELLED"
  const val NO_SPACE = "E_NO_SPACE"
  const val INVALID_IMAGE = "E_INVALID_IMAGE"
  const val FILE_MISSING = "E_FILE_MISSING"
  const val NO_CONTEXT = "E_NO_CONTEXT"
  const val NO_ACTIVITY = "E_NO_ACTIVITY"
  const val WALLPAPER_UNSUPPORTED = "E_WALLPAPER_UNSUPPORTED"
  const val WALLPAPER_NOT_ALLOWED = "E_WALLPAPER_NOT_ALLOWED"
  const val WALLPAPER_FAILED = "E_WALLPAPER_FAILED"
  const val SAVE_FAILED = "E_SAVE_FAILED"
  const val PERMISSION_REQUIRED = "E_PERMISSION_REQUIRED"
  const val SHARE_FAILED = "E_SHARE_FAILED"
  const val SIGNIN_CANCELLED = "E_SIGNIN_CANCELLED"
  const val SIGNIN_NO_ACCOUNT = "E_SIGNIN_NO_ACCOUNT"
  const val SIGNIN_CONFIG = "E_SIGNIN_CONFIG"
  const val SIGNIN_UNSUPPORTED = "E_SIGNIN_UNSUPPORTED"
  const val SIGNIN_INTERRUPTED = "E_SIGNIN_INTERRUPTED"
  const val SIGNIN_FAILED = "E_SIGNIN_FAILED"
  const val UNKNOWN = "E_UNKNOWN"
}

/** True when this exception (or a cause) is an out-of-storage error. */
internal fun Throwable.isNoSpace(): Boolean {
  var current: Throwable? = this
  var depth = 0
  while (current != null && depth < 8) {
    val message = current.message ?: ""
    if (message.contains("ENOSPC") || message.contains("No space left", ignoreCase = true)) return true
    current = current.cause
    depth += 1
  }
  return false
}
