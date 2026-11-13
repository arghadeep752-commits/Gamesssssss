package com.cameroplus.engine.camera

import expo.modules.kotlin.Promise
import expo.modules.kotlin.functions.Queues
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/** JavaScript entry point for the live camera: the view plus capture and control functions. */
class CameroCameraModule : Module() {
  private fun view(): CameroCameraView? = CameroCameraView.current?.get()

  override fun definition() = ModuleDefinition {
    Name("CameroCamera")

    AsyncFunction("takePhoto") { promise: Promise ->
      val session = view()?.session
      if (session == null) {
        promise.reject("E_NO_CAMERA", "The camera isn't open.", null)
      } else {
        session.takePhoto { result, error ->
          if (error != null || result == null) promise.reject("E_CAPTURE", error ?: "Capture failed", null)
          else promise.resolve(result)
        }
      }
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("startRecording") { promise: Promise ->
      val session = view()?.session
      if (session == null) {
        promise.reject("E_NO_CAMERA", "The camera isn't open.", null)
      } else {
        session.startRecording { error ->
          if (error != null) promise.reject("E_RECORD", error, null) else promise.resolve(null)
        }
      }
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("stopRecording") {
      view()?.session?.stopRecording()
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("pauseRecording") {
      view()?.session?.pauseRecording()
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("resumeRecording") {
      view()?.session?.resumeRecording()
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("setRecordingMuted") { muted: Boolean ->
      view()?.session?.muteRecording(muted)
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("setZoom") { ratio: Double ->
      view()?.session?.setZoom(ratio.toFloat())
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("setExposureIndex") { index: Int ->
      view()?.session?.setExposureIndex(index)
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("focusAt") { x: Double, y: Double, lock: Boolean ->
      val v = view() ?: return@AsyncFunction
      v.session?.focusAt(v.dpToPx(x.toFloat()), v.dpToPx(y.toFloat()), lock)
    }.runOnQueue(Queues.MAIN)

    AsyncFunction("resetFocus") {
      view()?.session?.resetFocus()
    }.runOnQueue(Queues.MAIN)

    View(CameroCameraView::class) {
      Events(
        "onReady", "onZoomChanged", "onFocusResult", "onRecordingEvent", "onPhotoEvent",
        "onCameraMetadata", "onOrientationChanged", "onPreviewState", "onCameraError"
      )

      Prop("active") { view: CameroCameraView, value: Boolean -> view.active = value }
      Prop("cameraId") { view: CameroCameraView, value: String? -> view.cameraId = value }
      Prop("mode") { view: CameroCameraView, value: String -> view.mode = value }
      Prop("aspect") { view: CameroCameraView, value: String -> view.aspect = value }
      Prop("photo") { view: CameroCameraView, value: String? -> view.photoJson = value }
      Prop("video") { view: CameroCameraView, value: String? -> view.videoJson = value }
      Prop("grade") { view: CameroCameraView, value: String? -> view.gradeJson = value }
      Prop("overlay") { view: CameroCameraView, value: String? -> view.overlayJson = value }
      Prop("flash") { view: CameroCameraView, value: String -> view.flash = value }
      Prop("torch") { view: CameroCameraView, value: Boolean -> view.torch = value }
      Prop("manual") { view: CameroCameraView, value: String? -> view.manualJson = value }
      Prop("timelapseIntervalMs") { view: CameroCameraView, value: Int -> view.timelapseIntervalMs = value }

      OnViewDidUpdateProps { view: CameroCameraView -> view.applyProps() }
      OnViewDestroys { view: CameroCameraView -> view.destroy() }
    }
  }
}
