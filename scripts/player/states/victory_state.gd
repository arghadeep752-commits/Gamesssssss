class_name PlayerVictoryState
extends PlayerState

var _hop := 0.0


func enter(_previous: String, _msg: Dictionary) -> void:
	var p := player
	p.controls_enabled = false
	p.play_anim("victory", true)
	_hop = 0.2


func physics_update(delta: float) -> void:
	var p := player
	p.apply_gravity(delta)
	p.velocity.x = move_toward(p.velocity.x, 0.0, 1800.0 * delta)
	_hop -= delta
	if _hop <= 0.0 and p.is_on_floor():
		_hop = 0.9
		p.velocity.y = -520.0
		Effects.burst(p.get_parent(), p.global_position + Vector2(0, -60), "star_04", Color(1, 0.9, 0.4), 8, 300.0, 0.6, 0.12, 300.0)
	p.move_and_slide()
