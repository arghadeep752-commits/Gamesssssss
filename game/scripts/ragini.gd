class_name Ragini
extends Node3D
## Ragini, the chudail. She patrols the school, follows noises, and chases you when she sees you.

signal caught
signal spotted

enum { PATROL, INVESTIGATE, CHASE, SEARCH, ATTACK, FROZEN }

var level: Level
var player: Player
var audio = null
var anim: AnimationPlayer
var state := PATROL
var path: Array = []
var path_i := 0
var repath_t := 0.0
var wait_t := 0.0
var lost_t := 0.0
var see_t := 0.0                # time since she last saw the player
var last_seen := Vector3.ZERO
var step_t := 0.0
var walk_speed := 1.9
var chase_speed := 3.3
var hearing := 1.0
var sight := 13.0
var cur_anim := ""
var laugh_t := 20.0
var eyes_light: OmniLight3D


func setup(mode: int) -> void:
	walk_speed = [1.5, 1.9, 2.4][mode]
	chase_speed = [2.7, 3.3, 3.9][mode]
	hearing = [0.6, 1.0, 1.5][mode]
	sight = [10.0, 13.0, 17.0][mode]


func build() -> bool:
	var p := "res://assets/models/ragini.glb"
	if not ResourceLoader.exists(p):
		return false
	var m: Node3D = load(p).instantiate()
	# Blender faces -Y, which is +Z in Godot; turn her so that she faces -Z like every other Godot character
	m.rotation.y = PI
	add_child(m)
	anim = _find_anim(m)
	if anim:
		for n in ["idle", "walk", "run"]:
			if anim.has_animation(n):
				anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	eyes_light = OmniLight3D.new()
	eyes_light.light_color = Color(1.0, 0.12, 0.05)
	eyes_light.light_energy = 0.7
	eyes_light.omni_range = 2.2
	eyes_light.position = Vector3(0, 1.6, -0.25)
	add_child(eyes_light)
	play("idle")
	return true


func _find_anim(n: Node) -> AnimationPlayer:
	if n is AnimationPlayer:
		return n
	for c in n.get_children():
		var r := _find_anim(c)
		if r:
			return r
	return null


func play(a: String, blend := 0.25, speed := 1.0) -> void:
	if anim == null or not anim.has_animation(a):
		return
	if cur_anim == a and anim.is_playing():
		anim.speed_scale = speed
		return
	cur_anim = a
	anim.play(a, blend, speed)


func eyes() -> Vector3:
	return global_position + Vector3(0, 1.58, 0)


func face_dir() -> Vector3:
	return -global_transform.basis.z


func can_see_player() -> bool:
	if player == null or player.hidden:
		return false
	var to := player.head() - eyes()
	var d := to.length()
	var rng := sight * (0.5 if player.crouched else 1.0)
	if d > rng:
		return false
	var flat := Vector3(to.x, 0, to.z).normalized()
	if d > 1.8 and face_dir().dot(flat) < 0.25:
		return false
	var q := PhysicsRayQueryParameters3D.create(eyes(), player.head() - Vector3(0, 0.15, 0), 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.is_empty()


func hear(pos: Vector3, radius: float) -> void:
	if state == CHASE or state == ATTACK or state == FROZEN:
		return
	if global_position.distance_to(pos) > radius * hearing * 2.2:
		return
	state = INVESTIGATE
	_go(pos)
	wait_t = 0.0


func _go(pos: Vector3) -> void:
	path = level.find_path(global_position, pos)
	path_i = 0
	repath_t = 0.6


func _pick_patrol() -> void:
	var pts: Array = level.meta["patrol"]
	var best := Vector3.ZERO
	# prefer points nearer the player a little, so the school never feels empty
	var tries := 3
	var best_d := 1e9
	for k in tries:
		var p = pts[randi() % pts.size()]
		var v := Vector3(p[0], 0, p[2])
		var d := v.distance_to(player.global_position) if player else 0.0
		if d < best_d and v.distance_to(global_position) > 5.0:
			best_d = d
			best = v
	if best == Vector3.ZERO:
		var p2 = pts[randi() % pts.size()]
		best = Vector3(p2[0], 0, p2[2])
	_go(best)


func _follow(dt: float, speed: float) -> bool:
	## moves along the path; returns true when the end is reached
	if path_i >= path.size():
		return true
	var tgt: Vector3 = path[path_i]
	var to := tgt - global_position
	to.y = 0
	var d := to.length()
	if d < 0.25:
		path_i += 1
		return path_i >= path.size()
	var dir := to / d
	global_position += dir * minf(speed * dt, d)
	global_position.y = 0.0
	var want := atan2(-dir.x, -dir.z)
	rotation.y = lerp_angle(rotation.y, want, clampf(dt * 7.0, 0, 1))
	_open_doors()
	step_t += dt * speed
	if step_t > 1.5:
		step_t = 0.0
		if audio:
			audio.play3d("payal", global_position + Vector3(0, 0.2, 0), -2.0, randf_range(0.95, 1.05))
			audio.play3d("footstep_%d" % randi_range(1, 6), global_position, -6.0, randf_range(0.78, 0.86))
	return false


func _open_doors() -> void:
	for k in level.doors:
		var d: Dictionary = level.doors[k]
		if d["open"] or d["lock"] == "main":
			continue
		var p: Vector3 = d["pos"]
		if Vector2(p.x - global_position.x, p.z - global_position.z).length() < 1.4:
			level.toggle_door(d, true)


func freeze(on: bool) -> void:
	state = FROZEN if on else PATROL
	if not on:
		path = []
		path_i = 0


func _process(dt: float) -> void:
	if level == null or player == null or state == FROZEN:
		return
	var sees := can_see_player()
	if sees:
		see_t = 0.0
		last_seen = player.global_position
	else:
		see_t += dt
	var dist := global_position.distance_to(player.global_position)
	match state:
		PATROL:
			play("walk", 0.3, walk_speed / 1.25)
			if sees:
				_start_chase()
			elif _follow(dt, walk_speed):
				wait_t += dt
				play("idle")
				if wait_t > 2.5:
					wait_t = 0.0
					_pick_patrol()
			laugh_t -= dt
			if laugh_t < 0.0:
				laugh_t = randf_range(25.0, 50.0)
				if audio and dist < 22.0:
					audio.play3d(["laugh", "whisper"][randi() % 2], global_position + Vector3(0, 1.5, 0), -4.0)
		INVESTIGATE:
			play("walk", 0.3, walk_speed * 1.25 / 1.25)
			if sees:
				_start_chase()
			elif _follow(dt, walk_speed * 1.25):
				play("idle")
				wait_t += dt
				rotation.y += dt * 1.2
				if wait_t > 3.5:
					wait_t = 0.0
					state = PATROL
					_pick_patrol()
		CHASE:
			play("run", 0.2, chase_speed / 3.3)
			repath_t -= dt
			if repath_t <= 0.0:
				_go(player.global_position if (sees or see_t < 1.5) else last_seen)
				repath_t = 0.35
			var hidden_seen := player.hidden and see_t < 2.0
			if dist < 1.35 and (sees or hidden_seen or see_t < 0.6):
				_attack()
				return
			var done := _follow(dt, chase_speed)
			if see_t > 5.0 or (done and see_t > 1.5):
				state = SEARCH
				wait_t = 0.0
				if audio:
					audio.set_vol("heartbeat", -60.0)
		SEARCH:
			play("idle")
			rotation.y += dt * 1.6
			wait_t += dt
			if sees:
				_start_chase()
			elif wait_t > 4.0:
				state = PATROL
				_pick_patrol()
		ATTACK:
			pass


func _start_chase() -> void:
	if state != CHASE:
		spotted.emit()
		if audio:
			audio.play3d("spotted", eyes(), 2.0)
	state = CHASE
	repath_t = 0.0


func _attack() -> void:
	state = ATTACK
	var to := player.global_position - global_position
	rotation.y = atan2(-to.x, -to.z)
	play("attack", 0.1, 1.3)
	caught.emit()
