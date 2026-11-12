class_name PlayerDeathState
extends PlayerState

var _timer := 0.0
var _sent := false


func enter(_previous: String, _msg: Dictionary) -> void:
	var p := player
	_timer = 1.25
	_sent = false
	p.play_anim("dead", true)
	p.velocity = Vector2(-p.facing * 160.0, -420.0)
	p.controls_enabled = false
	AudioManager.play_sfx("hit2", 0.0)
	Haptics.heavy()
	Events.camera_shake.emit(10.0, 0.35)


func physics_update(delta: float) -> void:
	var p := player
	_timer -= delta
	p.apply_gravity(delta)
	p.velocity.x = move_toward(p.velocity.x, 0.0, 600.0 * delta)
	p.move_and_slide()
	if _timer <= 0.0 and not _sent:
		_sent = true
		p.died.emit()
