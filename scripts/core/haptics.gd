extends Node
## Optional vibration feedback (respects the Vibration setting).


func vibrate(duration_ms := 30, amplitude := -1.0) -> void:
	if not bool(SaveManager.setting("vibration")):
		return
	if OS.has_feature("mobile"):
		Input.vibrate_handheld(duration_ms, amplitude)


func light() -> void:
	vibrate(15, 0.35)


func medium() -> void:
	vibrate(35, 0.6)


func heavy() -> void:
	vibrate(80, 1.0)
