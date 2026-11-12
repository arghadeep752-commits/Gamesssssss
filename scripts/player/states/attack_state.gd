class_name PlayerAttackState
extends PlayerState
## Weapon attack. Melee weapons hit on the swing frame; ranged weapons release a projectile.
## Pressing attack again near the end chains a combo swing.

var _hit_done := false
var _air := false
var _queued := false
var _combo := 0
var _hit_frame := 4


func enter(previous: String, msg: Dictionary) -> void:
	var p := player
	_air = not p.is_on_floor()
	_hit_done = false
	_queued = false
	_combo = int(msg.get("combo", 0))
	var w := p.weapon
	p.attack_cd = w.attack_cooldown
	var ranged := w.kind == "ranged"
	var anim := ""
	if ranged:
		anim = "jump_throw" if _air else "throw"
		_hit_frame = 3
	else:
		anim = "jump_attack" if _air else "attack"
		_hit_frame = 3
	p.play_anim(anim, true)
	p.sprite.speed_scale = w.attack_speed * (1.15 if _combo > 0 else 1.0)
	AudioManager.play_sfx("throw" if ranged else ("swing2" if _combo % 2 else "swing1"), 0.12, -2.0)


func physics_update(delta: float) -> void:
	var p := player
	p.apply_gravity(delta)
	if p.is_on_floor():
		p.velocity.x = move_toward(p.velocity.x, 0.0, Player.FRICTION * 1.4 * delta)
	else:
		p.move_horizontal(delta, p.input_x())
	p.move_and_slide()
	if _air:
		p.try_stomp()
	if p.wants_attack():
		_queued = true
	if _air and p.is_on_floor() and _hit_done:
		machine.change("idle")
		return
	if p.wants_special() and p.can_use_special() and _hit_done:
		machine.change("special_attack", {"action": "special"})


func on_frame_changed(frame: int) -> void:
	if frame == _hit_frame and not _hit_done:
		_hit_done = true
		player.perform_weapon_hit(_combo)


func on_animation_finished() -> void:
	var p := player
	p.sprite.speed_scale = 1.0
	if not _hit_done:
		_hit_done = true
		p.perform_weapon_hit(_combo)
	if _queued and _combo < 2:
		machine.change("attack", {"combo": _combo + 1})
		return
	if p.is_on_floor():
		machine.change("run" if absf(p.input_x()) > 0.05 else "idle")
	else:
		machine.change("fall")


func exit() -> void:
	player.sprite.speed_scale = 1.0
