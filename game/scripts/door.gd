extends Node3D
## A wooden door on a hinge: swings open when the player or Chaya walks up to it, closes again afterwards.

var leaf_dir := Vector3.RIGHT        # world direction hinge -> free end while closed
var plane_n := Vector3.BACK          # normal of the wall the door sits in
var locked := false
var actors: Array = []
var open_angle := 98.0
var reach := 1.8
var _cur := 0.0
var _target := 0.0
var _side := 1.0
var _hold := 0.0
var _lock_cd := 0.0
var _closing_sound := false
var forced := false                  # the cutscene / the ending moves this door itself

func _closest_actor() -> Node3D:
	var best: Node3D = null
	var bd := reach
	var mid := global_position + leaf_dir * 0.5
	for a in actors:
		if a == null:
			continue
		var p: Vector3 = a.global_position
		if absf(p.y - global_position.y) > 1.6:
			continue                     # someone on the other floor
		p.y = mid.y
		var d := p.distance_to(mid)
		if d < bd:
			bd = d
			best = a
	return best

## Swing the door to `deg` (0 = shut) on its own, ignoring who walks by, until release().
func force(deg: float, speed_sound := true) -> void:
	forced = true
	var t := deg_to_rad(deg)
	if speed_sound and absf(t) > 0.05 and absf(_target) < 0.05:
		Sfx.play_at("door_open", get_parent(), global_position + leaf_dir * 0.6, 0.0, 0.85)
	elif speed_sound and absf(t) < 0.05 and absf(_target) > 0.05:
		_closing_sound = true
	_target = t

func release() -> void:
	forced = false

func _process(dt: float) -> void:
	if forced:
		_cur = move_toward(_cur, _target, dt * 1.6)
		rotation.y = _cur
		if _closing_sound and absf(_target) < 0.05 and absf(_cur) < 0.02:
			_closing_sound = false
			Sfx.play_at("door_close", get_parent(), global_position + leaf_dir * 0.6, 2.0, 0.8)
		return
	var who := _closest_actor()
	_lock_cd = maxf(0.0, _lock_cd - dt)
	if who != null and locked:
		if _lock_cd <= 0.0 and who.has_method("add_shake"):
			_lock_cd = 2.5
			Sfx.play_at("door_locked", get_parent(), global_position + leaf_dir * 0.6, -2.0)
		who = null
	if who != null:
		_hold = 1.0
		if _target == 0.0:
			var rel := who.global_position - global_position
			var s := signf(rel.dot(plane_n))
			if s == 0.0:
				s = 1.0
			for sg in [1.0, -1.0]:
				var end := Basis(Vector3.UP, deg_to_rad(90.0 * sg)) * leaf_dir
				if signf(end.dot(plane_n)) == -s:
					_side = sg
			_target = deg_to_rad(open_angle) * _side
			_closing_sound = true
			Sfx.play_at("door_open", get_parent(), global_position + leaf_dir * 0.6, -1.0, randf_range(0.9, 1.1))
	else:
		_hold -= dt
		if _hold <= 0.0 and _target != 0.0:
			_target = 0.0
	var speed := 2.4
	_cur = move_toward(_cur, _target, dt * speed)
	rotation.y = _cur
	if _closing_sound and _target == 0.0 and absf(_cur) < 0.02:
		_closing_sound = false
		Sfx.play_at("door_close", get_parent(), global_position + leaf_dir * 0.6, -4.0, randf_range(0.9, 1.1))

func is_open() -> bool:
	return absf(_cur) > 0.35
