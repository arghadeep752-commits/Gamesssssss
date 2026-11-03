package app.hime

import android.app.PictureInPictureParams
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.media.AudioAttributes
import android.media.Ringtone
import android.media.RingtoneManager
import android.os.Build
import android.os.PowerManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Rational
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Hosts Flutter and the small amount of native glue calls need:
 * a foreground service, ringing, picture-in-picture and the proximity sensor.
 */
class MainActivity : FlutterActivity() {
    private var channel: MethodChannel? = null
    private var pipAllowed = false
    private var ringtone: Ringtone? = null
    private var vibrator: Vibrator? = null
    private var proximityLock: PowerManager.WakeLock? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val ch = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "app.hime/native")
        channel = ch
        ch.setMethodCallHandler { call, result ->
            when (call.method) {
                "startCallService" -> {
                    val video = call.argument<Boolean>("video") ?: false
                    val title = call.argument<String>("title") ?: "Hime"
                    startCallService(video, title)
                    result.success(true)
                }
                "stopCallService" -> {
                    stopService(Intent(this, CallService::class.java))
                    allowOverLockScreen(false)
                    result.success(true)
                }
                "setPipAllowed" -> {
                    pipAllowed = call.argument<Boolean>("allowed") ?: false
                    updatePipParams()
                    result.success(true)
                }
                "enterPip" -> result.success(enterPip())
                "startRinging" -> {
                    allowOverLockScreen(true)
                    startRinging()
                    result.success(true)
                }
                "stopRinging" -> {
                    stopRinging()
                    result.success(true)
                }
                "setProximity" -> {
                    setProximity(call.argument<Boolean>("enabled") ?: false)
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onDestroy() {
        stopRinging()
        setProximity(false)
        channel?.setMethodCallHandler(null)
        super.onDestroy()
    }

    // ------------------------------------------------------------------ call service

    private fun startCallService(video: Boolean, title: String) {
        val intent = Intent(this, CallService::class.java)
        intent.putExtra(CallService.EXTRA_VIDEO, video)
        intent.putExtra(CallService.EXTRA_TITLE, title)
        try {
            ContextCompat.startForegroundService(this, intent)
        } catch (e: Exception) {
            // The call keeps working while the app is visible even without the service.
        }
    }

    /** Lets the incoming-call screen appear over the lock screen only while a call is ringing or active. */
    private fun allowOverLockScreen(allow: Boolean) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(allow)
            setTurnScreenOn(allow)
        }
    }

    // ------------------------------------------------------------------ picture in picture

    private fun updatePipParams() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val params = PictureInPictureParams.Builder()
                .setAspectRatio(Rational(9, 16))
                .setAutoEnterEnabled(pipAllowed)
                .build()
            setPictureInPictureParams(params)
        }
    }

    private fun enterPip(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return false
        return try {
            val params = PictureInPictureParams.Builder().setAspectRatio(Rational(9, 16)).build()
            enterPictureInPictureMode(params)
        } catch (e: Exception) {
            false
        }
    }

    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        if (pipAllowed && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            enterPip()
        }
    }

    override fun onPictureInPictureModeChanged(isInPictureInPictureMode: Boolean, newConfig: Configuration) {
        super.onPictureInPictureModeChanged(isInPictureInPictureMode, newConfig)
        channel?.invokeMethod("pipChanged", isInPictureInPictureMode)
    }

    // ------------------------------------------------------------------ ringing

    private fun startRinging() {
        stopRinging()
        try {
            val uri = RingtoneManager.getActualDefaultRingtoneUri(this, RingtoneManager.TYPE_RINGTONE)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
            val r = RingtoneManager.getRingtone(this, uri)
            if (r != null) {
                r.audioAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    r.isLooping = true
                }
                r.play()
                ringtone = r
            }
        } catch (e: Exception) {
            ringtone = null
        }
        try {
            val v = obtainVibrator()
            val pattern = longArrayOf(0, 800, 800)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createWaveform(pattern, 0))
            } else {
                vibrateLegacy(v, pattern)
            }
            vibrator = v
        } catch (e: Exception) {
            vibrator = null
        }
    }

    private fun obtainVibrator(): Vibrator {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val manager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
            manager.defaultVibrator
        } else {
            legacyVibrator()
        }
    }

    @Suppress("DEPRECATION")
    private fun legacyVibrator(): Vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator

    @Suppress("DEPRECATION")
    private fun vibrateLegacy(v: Vibrator, pattern: LongArray) {
        v.vibrate(pattern, 0)
    }

    private fun stopRinging() {
        try {
            ringtone?.stop()
        } catch (e: Exception) {
        }
        ringtone = null
        try {
            vibrator?.cancel()
        } catch (e: Exception) {
        }
        vibrator = null
    }

    // ------------------------------------------------------------------ proximity

    private fun setProximity(enabled: Boolean) {
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            if (enabled) {
                if (proximityLock == null && pm.isWakeLockLevelSupported(PowerManager.PROXIMITY_SCREEN_OFF_WAKE_LOCK)) {
                    proximityLock = pm.newWakeLock(PowerManager.PROXIMITY_SCREEN_OFF_WAKE_LOCK, "hime:proximity")
                }
                val lock = proximityLock
                if (lock != null && !lock.isHeld) lock.acquire(60L * 60L * 1000L)
            } else {
                val lock = proximityLock
                if (lock != null && lock.isHeld) lock.release()
            }
        } catch (e: Exception) {
        }
    }
}
