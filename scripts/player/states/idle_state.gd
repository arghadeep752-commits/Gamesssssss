class_name PlayerIdleState
extends PlayerState


func enter(_previous: String, _msg: Dictionary) -> void:
	player.play_anim("idle")


func physics_update(delta: float) -> void:
	var p := player
	p.apply_gravity(delta)
	p.move_horizontal(delta, 0.0)
	p.move_and_slide()
	if common_transitions():
		return
	if p.consume_jump():
		machine.change("jump")
		return
	if not p.is_on_floor():
		p.coyote = Player.COYOTE_TIME
		machine.change("fall")
		return
	if absf(p.input_x()) > 0.05:
		machine.change("run")
