class_name PlayerJumpState
extends PlayerState


func enter(previous: String, msg: Dictionary) -> void:
	var p := player
	var air := bool(msg.get("air", false))
	var power: float = msg.get("power", p.jump_velocity() * (0.86 if air else 1.0))
	p.velocity.y = -power
	p.coyote = 0.0
	p.jump_buffer = 0.0
	p.play_anim("jump", true)
	if air:
		p.air_jumps_used += 1
		Effects.flash(p.get_parent(), p.global_position + Vector2(0, -10), "circle_05", Color(0.7, 0.9, 1, 0.8), 0.15, 0.6, 0.25)
		AudioManager.play_sfx("jump", 0.05, -2.0)
	elif not msg.get("spring", false):
		Effects.dust(p.get_parent(), p.global_position)
		AudioManager.play_sfx("jump", 0.05, -4.0)


func physics_update(delta: float) -> void:
	var p := player
	if not Input.is_action_pressed("jump") and p.velocity.y < -300.0 and not p.spring_boost:
		p.velocity.y *= 0.55   # variable jump height
	p.apply_gravity(delta)
	p.move_horizontal(delta, p.input_x())
	p.move_and_slide()
	if p.is_on_ceiling():
		p.velocity.y = max(p.velocity.y, 60.0)
		p.bump_head()
	if common_transitions():
		return
	if p.consume_jump(true):
		machine.change("jump", {"air": true})
		return
	if p.velocity.y >= 0.0:
		machine.change("fall")
