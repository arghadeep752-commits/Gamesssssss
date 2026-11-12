class_name PlayerRunState
extends PlayerState

var _step := 0.0


func enter(_previous: String, _msg: Dictionary) -> void:
	player.play_anim("run")
	_step = 0.1


func physics_update(delta: float) -> void:
	var p := player
	var dir := p.input_x()
	p.apply_gravity(delta)
	p.move_horizontal(delta, dir)
	p.move_and_slide()
	p.sprite.speed_scale = clampf(absf(p.velocity.x) / 340.0, 0.6, 1.6)
	_step -= delta * clampf(absf(p.velocity.x) / 340.0, 0.5, 1.6)
	if _step <= 0.0:
		_step = 0.27
		AudioManager.play_sfx("footstep%d" % (randi() % 3 + 1), 0.1, -10.0)
	if common_transitions():
		return
	if p.consume_jump():
		machine.change("jump")
		return
	if not p.is_on_floor():
		p.coyote = Player.COYOTE_TIME
		machine.change("fall")
		return
	if absf(dir) <= 0.05 and absf(p.velocity.x) < 40.0:
		machine.change("idle")


func exit() -> void:
	player.sprite.speed_scale = 1.0
