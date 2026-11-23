extends AnimatableBody3D
## One drawer of the dresser: USE slides it open, USE again slides it shut.
## Made by dresser.gd; the drawer's 3D model moves together with this collider.

var display_name := "DRAWER"

var _model: Node3D
var _pull := Vector3.ZERO
var _sound: AudioStreamPlayer3D
var _open := false
var _busy := false
var _body_closed := Vector3.ZERO
var _model_closed := Vector3.ZERO


func setup(model_part: Node3D, pull: Vector3, sound: AudioStreamPlayer3D) -> void:
	_model = model_part
	_pull = pull
	_sound = sound
	_body_closed = global_position
	_model_closed = model_part.global_position


func interact() -> void:
	if _busy:
		return
	_busy = true
	_open = not _open
	_sound.global_position = global_position
	_sound.pitch_scale = 1.0 if _open else 1.15
	_sound.play()
	var shift := _pull if _open else Vector3.ZERO
	var tween := create_tween().set_parallel(true).set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)
	tween.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "global_position", _body_closed + shift, 0.45)
	tween.tween_property(_model, "global_position", _model_closed + shift, 0.45)
	tween.chain().tween_callback(func() -> void: _busy = false)
