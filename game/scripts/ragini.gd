class_name Ragini
extends Node3D
## Moulika ma'am, the school's ghost (a Hyper3D Rodin character, rigged and animated by Rodin).
## She patrols the school, follows noises, and chases you when she sees you.

const MODEL := "res://assets/models/moulika.glb"
const HEIGHT := 1.68
# which Rodin animation plays as which move: [clip, from s, to s] (to = 0: the whole clip)
const CLIPS := {
	"idle": ["human_000050", 0.0, 0.0],      # sad idle, head bowed
	"walk": ["human_000089", 0.0, 0.0],      # walking
	"run": ["human_000049", 0.0, 0.0],       # running with her hands reaching forward
	"attack": ["human_000064", 0.35, 1.25],  # raising a hand and striking down
	"scream": ["human_000041", 1.3, 3.2],    # raising her arm and pointing at you
}

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
var walk_nat := 1.25            # metres per second the walk clip covers at speed 1 (measured from the clip)
var run_nat := 3.3
var eye_h := HEIGHT - 0.12


func setup(mode: int) -> void:
	walk_speed = [1.5, 1.9, 2.4][mode]
	chase_speed = [2.7, 3.3, 3.9][mode]
	hearing = [0.6, 1.0, 1.5][mode]
	sight = [10.0, 13.0, 17.0][mode]


func build() -> bool:
	if not ResourceLoader.exists(MODEL):
		return false
	var m: Node3D = load(MODEL).instantiate()
	# scale her to HEIGHT and stand her feet on the floor
	var box := _mesh_box(m, m, Transform3D.IDENTITY)
	var s := HEIGHT / maxf(box.size.y, 0.01)
	m.scale = Vector3.ONE * s
	m.position.y = -box.position.y * s
	# Rodin characters face +Z; turn her so that she faces -Z like every other Godot character
	m.rotation.y = PI
	add_child(m)
	anim = _find_anim(m)
	if anim:
		_make_clips(s)
	# a faint cold glow, so she can be made out in the dark corridors
	eyes_light = OmniLight3D.new()
	eyes_light.light_color = Color(0.72, 0.8, 1.0)
	eyes_light.light_energy = 0.35
	eyes_light.omni_range = 2.2
	eyes_light.position = Vector3(0, 1.35, -0.55)
	add_child(eyes_light)
	play("idle")
	return true


func _mesh_box(n: Node, top: Node, xf: Transform3D) -> AABB:
	## bind-pose bounds of every mesh under `top`, in top's space
	var t := xf if n == top else xf * (n as Node3D).transform if n is Node3D else xf
	var box := AABB()
	var have := false
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		box = t * (n as MeshInstance3D).mesh.get_aabb()
		have = true
	for c in n.get_children():
		var b := _mesh_box(c, top, t)
		if b.size != Vector3.ZERO:
			box = b if not have else box.merge(b)
			have = true
	return box


func _make_clips(s: float) -> void:
	## the game's moves, made from the Rodin clips: trimmed, looped, and walked in place (the code moves her)
	var lib: AnimationLibrary = anim.get_animation_library("")
	for move in CLIPS:
		var c: Array = CLIPS[move]
		if not anim.has_animation(c[0]):
			continue
		var src: Animation = anim.get_animation(c[0])
		var a: Animation = _subclip(src, c[1], c[2]) if c[2] > c[1] else src.duplicate(true)
		var d := _strip_root(a)
		a.loop_mode = Animation.LOOP_LINEAR if move in ["idle", "walk", "run"] else Animation.LOOP_NONE
		if move == "walk" and d > 0.1:
			walk_nat = d / a.length * s
		elif move == "run" and d > 0.1:
			run_nat = d / a.length * s
		lib.add_animation(move, a)


func _subclip(src: Animation, t0: float, t1: float) -> Animation:
	var a := Animation.new()
	a.length = t1 - t0
	for t in src.get_track_count():
		var ty := src.track_get_type(t)
		if ty != Animation.TYPE_POSITION_3D and ty != Animation.TYPE_ROTATION_3D and ty != Animation.TYPE_SCALE_3D:
			continue
		var nt := a.add_track(ty)
		a.track_set_path(nt, src.track_get_path(t))
		a.track_set_interpolation_type(nt, src.track_get_interpolation_type(t))
		var times: Array = [t0]
		for k in src.track_get_key_count(t):
			var kt := src.track_get_key_time(t, k)
			if kt > t0 + 0.001 and kt < t1 - 0.001:
				times.append(kt)
		times.append(t1)
		for kt in times:
			match ty:
				Animation.TYPE_POSITION_3D:
					a.position_track_insert_key(nt, kt - t0, src.position_track_interpolate(t, kt))
				Animation.TYPE_ROTATION_3D:
					a.rotation_track_insert_key(nt, kt - t0, src.rotation_track_interpolate(t, kt))
				Animation.TYPE_SCALE_3D:
					a.scale_track_insert_key(nt, kt - t0, src.scale_track_interpolate(t, kt))
	return a


func _strip_root(a: Animation) -> float:
	## removes the forward travel from the hips track; returns how far the clip walked (model units)
	for t in a.get_track_count():
		if a.track_get_type(t) != Animation.TYPE_POSITION_3D:
			continue
		var n := a.track_get_key_count(t)
		if n < 2:
			continue
		var p0: Vector3 = a.track_get_key_value(t, 0)
		var p1: Vector3 = a.track_get_key_value(t, n - 1)
		var d := Vector3(p1.x - p0.x, 0.0, p1.z - p0.z)
		var T := a.track_get_key_time(t, n - 1)
		if d.length() < 0.05 or T <= 0.0:
			return 0.0
		for k in n:
			var v: Vector3 = a.track_get_key_value(t, k)
			a.track_set_key_value(t, k, v - d * (a.track_get_key_time(t, k) / T))
		return d.length()
	return 0.0


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
	return global_position + Vector3(0, eye_h, 0)


func _move_anim(speed: float) -> void:
	## walk, or run once walking would look rushed
	if speed / walk_nat <= 1.45:
		play("walk", 0.3, speed / walk_nat)
	else:
		play("run", 0.3, speed / run_nat)


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
			_move_anim(walk_speed)
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
			_move_anim(walk_speed * 1.25)
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
			play("run", 0.2, chase_speed / run_nat)
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
