package com.cameroplus.engine.edit

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/** Editor preview surface for photos and videos. */
class CameroCanvasModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("CameroCanvas")

    View(CameroCanvasView::class) {
      Events("onCanvasLayout", "onVideoInfo", "onVideoProgress", "onCanvasError")

      Prop("source") { view: CameroCanvasView, value: String? -> view.pendingSource = value }
      Prop("kind") { view: CameroCanvasView, value: String -> view.pendingKind = value }
      Prop("grade") { view: CameroCanvasView, value: String? -> view.setGrade(value) }
      Prop("transform") { view: CameroCanvasView, value: String? -> view.setTransform(value) }
      Prop("compare") { view: CameroCanvasView, value: Boolean -> view.setCompare(value) }
      Prop("cropMode") { view: CameroCanvasView, value: Boolean -> view.setCropMode(value) }
      Prop("inset") { view: CameroCanvasView, value: Double -> view.setInset(value.toFloat()) }
      Prop("playing") { view: CameroCanvasView, value: Boolean -> view.playing = value }
      Prop("muted") { view: CameroCanvasView, value: Boolean -> view.muted = value }
      Prop("speed") { view: CameroCanvasView, value: Double -> view.speed = value.toFloat() }
      Prop("trimStartMs") { view: CameroCanvasView, value: Double -> view.trimStartMs = value.toLong() }
      Prop("trimEndMs") { view: CameroCanvasView, value: Double -> view.trimEndMs = value.toLong() }
      Prop("seekMs") { view: CameroCanvasView, value: Double -> view.pendingSeek = value.toLong() }

      OnViewDidUpdateProps { view: CameroCanvasView -> view.commitProps() }
      OnViewDestroys { view: CameroCanvasView -> view.destroy() }
    }
  }
}
