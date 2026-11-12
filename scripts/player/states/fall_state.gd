class_name PlayerFallState
extends PlayerState
## Falling. Holding JUMP (after a fresh press, when no air-jump is left) opens the glider.

var _gliding := false
var _glide_armed := false
var _peak_speed := 0.0


func enter(_previous: String, _msg: Dictionary) -> void:
	_gliding = false
	_glide_armed = false
	_peak_speed = 0.0
	player.play_anim("fall")


func physics_update(delta: float) -> void:
	var p := player
	p.coyote -= delta
	if Input.is_action_just_pressed("jump") and p.coyote <= 0.0 and not p.has_air_jump():
		_glide_armed = true
	if not Input.is_action_pressed("jump"):
		_glide_armed = false
	var glide := _glide_armed and p.velocity.y > 40.0
	if glide != _gliding:
		_gliding = glide
		p.play_anim("glide" if glide else "fall")
	p.apply_gravity(delta)
	if _gliding:
		p.velocity.y = min(p.velocity.y, Player.GLIDE_FALL)
	p.move_horizontal(delta, p.input_x())
	_peak_speed = max(_peak_speed, p.velocity.y)
	p.move_and_slide()
	p.try_stomp()
	if common_transitions():
		return
	if p.coyote > 0.0 and p.consume_jump():
		machine.change("jump")
		return
	if p.has_air_jump() and p.consume_jump(true):
		machine.change("jump", {"air": true})
		return
	if p.is_on_floor():
		p.land(_peak_speed)
		if p.consume_jump():
			machine.change("jump")
			return
		machine.change("run" if absf(p.input_x()) > 0.05 else "idle")
