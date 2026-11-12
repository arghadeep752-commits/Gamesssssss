class_name PlayerHurtState
extends PlayerState

var _timer := 0.0


func enter(_previous: String, msg: Dictionary) -> void:
	var p := player
	_timer = 0.32
	p.play_anim("hurt", true)
	var from: Vector2 = msg.get("from", p.global_position + Vector2(-p.facing * 10, 0))
	var knock: float = msg.get("knock", 520.0)
	var dir := signf(p.global_position.x - from.x)
	if dir == 0:
		dir = -p.facing
	p.velocity = Vector2(dir * knock, -knock * 0.75)


func physics_update(delta: float) -> void:
	var p := player
	_timer -= delta
	p.apply_gravity(delta)
	p.velocity.x = move_toward(p.velocity.x, 0.0, 900.0 * delta)
	p.move_and_slide()
	if _timer <= 0.0:
		machine.change("idle" if p.is_on_floor() else "fall")
