class_name PlayerClimbState
extends PlayerState
## Climbing designated ladders.


func enter(_previous: String, _msg: Dictionary) -> void:
	var p := player
	p.play_anim("climb")
	p.velocity = Vector2.ZERO
	var lad := p.current_ladder()
	if lad:
		p.global_position.x = lad.global_position.x
	p.climbing = true


func exit() -> void:
	player.climbing = false
	player.sprite.speed_scale = 1.0


func physics_update(delta: float) -> void:
	var p := player
	var lad := p.current_ladder()
	if lad == null:
		machine.change("fall")
		return
	var v := Input.get_axis("move_up", "move_down")
	p.velocity = Vector2(0, v * Player.CLIMB_SPEED)
	p.sprite.speed_scale = absf(v)
	p.move_and_slide()
	if p.consume_jump():
		machine.change("jump", {"power": p.jump_velocity() * 0.85})
		return
	if p.wants_attack():
		machine.change("attack")
		return
	if v > 0.0 and p.is_on_floor():
		machine.change("idle")
		return
	var top: float = lad.get_meta("top_y", -INF)
	if v < 0.0 and p.global_position.y <= top + 2.0:
		p.global_position.y = top - 1.0
		p.velocity = Vector2.ZERO
		machine.change("idle")
