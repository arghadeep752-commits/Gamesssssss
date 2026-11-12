class_name PlayerSpecialState
extends PlayerState
## SPECIAL_ATTACK: character specials (energy) and weapon abilities (cooldown).

var _action := "special"
var _id := ""
var _done := false
var _timer := 0.0
var _dash_dir := 1.0
var _hits := {}


func enter(_previous: String, msg: Dictionary) -> void:
	var p := player
	_action = str(msg.get("action", "special"))
	_done = false
	_hits.clear()
	if _action == "special":
		_id = p.data.special_id
		p.spend_special()
	else:
		_id = p.weapon.ability_id
		p.ability_cd = p.weapon.ability_cooldown
	_dash_dir = p.facing
	_timer = 0.0
	AudioManager.play_sfx("special", 0.05)
	Haptics.medium()
	match _id:
		"shadow_dash", "dash_slash":
			p.play_anim("slide" if _id == "shadow_dash" else "attack", true)
			p.invuln = max(p.invuln, 0.45)
			p.velocity = Vector2(_dash_dir * (1100.0 if _id == "shadow_dash" else 950.0), 0)
			_timer = 0.32 if _id == "shadow_dash" else 0.24
			if _id == "shadow_dash":
				p.sprite.modulate = Color(0.5, 0.35, 0.9, 0.55)
		"rising_slash":
			p.play_anim("jump_attack", true)
			p.velocity.y = -p.jump_velocity() * 1.05
			_timer = 0.45
		"whirlwind":
			p.play_anim("jump_attack", true)
			p.sprite.speed_scale = 1.6
			_timer = 0.55
		_:
			p.play_anim("jump_throw" if not p.is_on_floor() else "throw", true)
			_timer = 0.36


func physics_update(delta: float) -> void:
	var p := player
	_timer -= delta
	match _id:
		"shadow_dash", "dash_slash":
			p.velocity.y = 0.0
			p.move_and_slide()
			p.spawn_afterimage()
			p.dash_hits(_hits, 34.0 if _id == "dash_slash" else 26.0)
			if _timer <= 0.0 or p.is_on_wall():
				p.velocity.x *= 0.25
				_finish()
		"rising_slash":
			p.apply_gravity(delta)
			p.move_horizontal(delta, p.input_x())
			p.move_and_slide()
			if not _done and _timer < 0.3:
				_done = true
				p.do_special_effect(_id)
			if _timer <= 0.0:
				_finish()
		"whirlwind":
			p.apply_gravity(delta)
			p.move_horizontal(delta, p.input_x() * 0.6)
			p.move_and_slide()
			if int(_timer * 10.0) % 2 == 0:
				p.area_hit(130.0, p.weapon_damage() * 0.6, _hits, 0.18)
			if _timer <= 0.0:
				_finish()
		_:
			p.apply_gravity(delta)
			p.velocity.x = move_toward(p.velocity.x, 0.0, 2400.0 * delta)
			p.move_and_slide()
			if not _done and _timer < 0.24:
				_done = true
				p.do_special_effect(_id)
			if _timer <= 0.0:
				_finish()


func _finish() -> void:
	var p := player
	p.sprite.modulate = Color.WHITE
	p.sprite.speed_scale = 1.0
	if p.is_on_floor():
		machine.change("idle")
	else:
		machine.change("fall")


func exit() -> void:
	player.sprite.modulate = Color.WHITE
	player.sprite.speed_scale = 1.0
