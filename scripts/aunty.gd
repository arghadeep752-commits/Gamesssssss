extends CharacterBody3D
## Scary Aunty: walks around all 3 floors on waypoints, opens doors,
## chases the player when she sees or hears them, and catches them.

enum { PATROL, WAIT, INVESTIGATE, CHASE, SEARCH, FROZEN }

const WALK_SPEED := 2.3
const CHASE_SPEED := 5.0
const VIEW_DIST := 15.0
const VIEW_ANGLE := 65.0
const CATCH_DIST := 1.15
const GRAVITY := 20.0

const SPOT_LINES := ["I SEE YOU!", "Come here, naughty boy!", "Where do you think you're going?!", "You can't escape from Aunty!"]
const HEAR_LINES := ["What was that noise?", "Who's there?", "I heard that!"]
const LOST_LINES := ["Hmph... where did he go?", "You can't hide forever!"]

var game
var house
var astar: AStar3D
var state := FROZEN
var path := PackedInt64Array()
var path_i := 0
var wait_time := 0.0
var last_seen := Vector3.ZERO
var lost_time := 0.0
var sees_player := false

var visual: Node3D
var anim: AnimationPlayer
var walk_anim := ""
var run_anim := ""
var idle_anim := ""
var arm_l: Node3D
var arm_r: Node3D
var step_audio: AudioStreamPlayer3D

var _vision_t := 0.0
var _repath_t := 0.0
var _force_path_t := 0.0
var _stuck_t := 0.0
var _stuck_pos := Vector3.ZERO
var _stuck_count := 0
var _step_accum := 0.0
var _anim_t := 0.0
var _voice_cd := 0.0


func setup(g, h) -> void:
	game = g
	house = h
	astar = h.astar
	collision_layer = 4
	collision_mask = 1
	floor_snap_length = 0.6
	floor_max_angle = deg_to_rad(50.0)
	floor_constant_speed = true
	var shape := CapsuleShape3D.new()
	shape.radius = 0.3
	shape.height = 1.7
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position = Vector3(0, 0.85, 0)
	add_child(cs)
	_make_visual()
	step_audio = AudioStreamPlayer3D.new()
	step_audio.unit_size = 6.0
	step_audio.max_distance = 30.0
	step_audio.position = Vector3(0, 0.2, 0)
	add_child(step_audio)


func _make_visual() -> void:
	# Sketchfab character if it was downloaded (glTF faces +Z, so turn it around).
	var model: Node3D = Assets.make_model("aunty", Vector3(0.7, 1.72, 0.5), "height", PI)
	if model != null:
		visual = model
		add_child(model)
		var players := model.find_children("*", "AnimationPlayer", true, false)
		if players.size() > 0:
			anim = players[0] as AnimationPlayer
			var names := anim.get_animation_list()
			for n in names:
				var low := String(n).to_lower()
				if walk_anim == "" and low.contains("walk"):
					walk_anim = n
				elif run_anim == "" and low.contains("run"):
					run_anim = n
				elif idle_anim == "" and low.contains("idle"):
					idle_anim = n
			if walk_anim == "" and names.size() > 0:
				walk_anim = names[0]
			if run_anim == "":
				run_anim = walk_anim
			for n in [walk_anim, run_anim, idle_anim]:
				if n != "" and anim.has_animation(n):
					anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	else:
		visual = house.fb.make_aunty()
		add_child(visual)
		arm_l = visual.get_node_or_null("ArmL") as Node3D
		arm_r = visual.get_node_or_null("ArmR") as Node3D
	Assets.set_layers_recursive(visual, 1)


# ---------------------------------------------------------------- control from the game

func activate(delay: float) -> void:
	state = WAIT
	wait_time = delay


func freeze() -> void:
	state = FROZEN
	velocity = Vector3.ZERO


func respawn(pos: Vector3) -> void:
	global_position = pos
	velocity = Vector3.ZERO
	path = PackedInt64Array()
	path_i = 0
	sees_player = false
	state = FROZEN


func hear(pos: Vector3, radius: float) -> void:
	if state == FROZEN or state == CHASE:
		return
	if global_position.distance_to(pos) > radius:
		return
	last_seen = pos
	if _path_to(pos):
		state = INVESTIGATE
		_say(HEAR_LINES)


# ---------------------------------------------------------------- main loop

func _physics_process(delta: float) -> void:
	if game == null:
		return
	_voice_cd = maxf(_voice_cd - delta, 0.0)
	_force_path_t = maxf(_force_path_t - delta, 0.0)
	var want := Vector3.ZERO
	match state:
		WAIT:
			wait_time -= delta
			if wait_time <= 0.0:
				_pick_patrol()
		PATROL, INVESTIGATE, SEARCH:
			var spd := WALK_SPEED * (1.35 if state == INVESTIGATE else 1.0)
			want = _follow_path(spd)
			if path_i >= path.size():
				_start_wait(randf_range(1.0, 3.0))
		CHASE:
			want = _chase(delta)

	if state != FROZEN:
		_vision_t -= delta
		if _vision_t <= 0.0:
			_vision_t = 0.15
			sees_player = _can_see_player()
			if sees_player:
				last_seen = game.player.global_position
				lost_time = 0.0
				if state != CHASE:
					_start_chase()

	velocity.x = want.x
	velocity.z = want.z
	if is_on_floor():
		velocity.y = -0.5
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()

	var speed_now := Vector2(velocity.x, velocity.z).length()
	if speed_now > 0.2:
		var face := atan2(-velocity.x, -velocity.z)
		rotation.y = lerp_angle(rotation.y, face, minf(1.0, delta * 8.0))
	_open_doors_near()
	_check_stuck(delta)
	_animate(delta, speed_now)
	_steps(delta, speed_now)


func _start_wait(t: float) -> void:
	state = WAIT
	wait_time = t


func _pick_patrol() -> void:
	var pts: Array = house.patrol_points
	var candidates: Array = []
	for id in pts:
		if not astar.is_point_disabled(id):
			candidates.append(id)
	if candidates.is_empty():
		_start_wait(2.0)
		return
	# Half of the time she walks on the same floor as the player.
	if randf() < 0.55:
		var pf: int = game.player_floor()
		var same: Array = []
		for id in candidates:
			if house.floor_of_point(id) == pf:
				same.append(id)
		if not same.is_empty():
			candidates = same
	var target_id: int = candidates[randi() % candidates.size()]
	if _path_to(astar.get_point_position(target_id)):
		state = PATROL
	else:
		_start_wait(1.5)


## Closest waypoint that can be reached in a straight line (no wall between).
func _closest_point(pos: Vector3) -> int:
	var best: Array = []
	for id in astar.get_point_ids():
		if astar.is_point_disabled(id):
			continue
		var d := astar.get_point_position(id).distance_squared_to(pos)
		best.append([d, id])
	if best.is_empty():
		return -1
	best.sort_custom(func(a, b): return a[0] < b[0])
	var space := get_world_3d().direct_space_state
	for i in range(mini(5, best.size())):
		var id: int = best[i][1]
		var p := astar.get_point_position(id)
		var q := PhysicsRayQueryParameters3D.create(pos + Vector3(0, 0.6, 0), p + Vector3(0, 0.5, 0), 1)
		if space.intersect_ray(q).is_empty():
			return id
	return int(best[0][1])


func _path_to(pos: Vector3) -> bool:
	var from_id := _closest_point(global_position)
	var to_id := _closest_point(pos)
	if from_id == -1 or to_id == -1:
		return false
	path = astar.get_id_path(from_id, to_id)
	path_i = 0
	if path.size() > 1:
		var p0 := astar.get_point_position(path[0])
		var p1 := astar.get_point_position(path[1])
		if global_position.distance_to(p1) < p0.distance_to(p1):
			path_i = 1
	return path.size() > 0


func _follow_path(speed: float) -> Vector3:
	while path_i < path.size():
		var p := astar.get_point_position(path[path_i])
		var to := p - global_position
		to.y = 0.0
		if to.length() < 0.45 and absf(p.y - global_position.y) < 1.7:
			path_i += 1
			continue
		return to.normalized() * speed
	return Vector3.ZERO


# ---------------------------------------------------------------- seeing + chasing

func _can_see_player() -> bool:
	if not game.player_can_be_seen():
		return false
	var eye := global_position + Vector3(0, 1.6, 0)
	var target: Vector3 = game.player.global_position + Vector3(0, 1.3, 0)
	var to := target - eye
	var dist := to.length()
	if dist > VIEW_DIST or absf(to.y) > 2.3:
		return false
	var flat := Vector3(to.x, 0.0, to.z)
	if dist > 2.2 and flat.length() > 0.01:
		var fwd := -global_transform.basis.z
		var ang := rad_to_deg(fwd.angle_to(flat.normalized()))
		if ang > VIEW_ANGLE:
			return false
	var q := PhysicsRayQueryParameters3D.create(eye, target, 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _start_chase() -> void:
	state = CHASE
	path = PackedInt64Array()
	path_i = 0
	_repath_t = 0.0
	game.on_aunty_chase_start()
	_say(SPOT_LINES)


func _chase(delta: float) -> Vector3:
	var ppos: Vector3 = game.player.global_position
	var flat := Vector3(ppos.x - global_position.x, 0.0, ppos.z - global_position.z)
	var dy := absf(ppos.y - global_position.y)
	if sees_player:
		if flat.length() < CATCH_DIST and dy < 1.3:
			freeze()
			game.on_caught()
			return Vector3.ZERO
		if dy < 1.0 and _force_path_t <= 0.0:
			return flat.normalized() * CHASE_SPEED
	else:
		lost_time += delta
		if lost_time > 6.0:
			game.on_aunty_chase_end()
			_say(LOST_LINES)
			if _path_to(last_seen):
				state = SEARCH
			else:
				_start_wait(2.0)
			return Vector3.ZERO
	_repath_t -= delta
	if _repath_t <= 0.0 or path_i >= path.size():
		_repath_t = 0.6
		_path_to(last_seen)
	var v := _follow_path(CHASE_SPEED)
	if v == Vector3.ZERO:
		var to_last := Vector3(last_seen.x - global_position.x, 0.0, last_seen.z - global_position.z)
		if to_last.length() > 0.4:
			return to_last.normalized() * CHASE_SPEED * 0.8
	return v


# ---------------------------------------------------------------- doors, stuck, animation, sound

func _open_doors_near() -> void:
	if state == FROZEN or state == WAIT:
		return
	for d in house.doors:
		if d.is_open or d.locked:
			continue
		var dp: Vector3 = d.global_position
		if absf(dp.y - global_position.y) > 1.5:
			continue
		if Vector2(dp.x - global_position.x, dp.z - global_position.z).length() < 1.4:
			d.set_open(true)


func _check_stuck(delta: float) -> void:
	var moving := state == PATROL or state == INVESTIGATE or state == SEARCH or state == CHASE
	if not moving:
		_stuck_t = 0.0
		_stuck_pos = global_position
		return
	_stuck_t += delta
	if _stuck_t < 1.2:
		return
	var moved := global_position.distance_to(_stuck_pos)
	_stuck_pos = global_position
	_stuck_t = 0.0
	if moved > 0.25:
		_stuck_count = 0
		return
	_stuck_count += 1
	_force_path_t = 2.5
	if _stuck_count >= 3 and path_i < path.size():
		# Hop to the next waypoint so she never gets stuck forever.
		global_position = astar.get_point_position(path[path_i]) + Vector3(0, 0.05, 0)
		_stuck_count = 0
	elif state != CHASE and path.size() > 0:
		_path_to(astar.get_point_position(path[path.size() - 1]))


func _animate(delta: float, speed_now: float) -> void:
	if anim != null:
		var want := idle_anim
		if speed_now > 3.2:
			want = run_anim
		elif speed_now > 0.3:
			want = walk_anim
		if want == "":
			want = walk_anim
		if want == "":
			return
		if String(anim.current_animation) != want:
			anim.play(want, 0.2)
		if speed_now > 0.3:
			var base := CHASE_SPEED if want == run_anim and run_anim != walk_anim else WALK_SPEED
			anim.speed_scale = clampf(speed_now / base, 0.6, 2.0)
		elif want == idle_anim:
			anim.speed_scale = 1.0
		else:
			anim.speed_scale = 0.0
		return
	# Stand-in model: swing arms, raise the rolling pin while chasing.
	_anim_t += delta * speed_now * 3.0
	var amount := clampf(speed_now / 3.0, 0.0, 1.0)
	var swing := sin(_anim_t) * amount * 0.7
	if arm_l != null:
		arm_l.rotation.x = swing
	if arm_r != null:
		var raise := -2.2 if state == CHASE else 0.0
		arm_r.rotation.x = lerpf(arm_r.rotation.x, raise - swing, minf(1.0, delta * 10.0))
	if visual != null:
		visual.position.y = absf(sin(_anim_t)) * 0.035 * amount


func _steps(delta: float, speed_now: float) -> void:
	if speed_now < 0.4 or not is_on_floor():
		return
	_step_accum += speed_now * delta
	var stride := 1.5 if state == CHASE else 1.05
	if _step_accum < stride:
		return
	_step_accum = 0.0
	var s := Assets.get_sound("aunty_step")
	if s == null:
		s = Assets.get_sound("step_wood")
	if s == null:
		return
	step_audio.stream = s
	step_audio.pitch_scale = randf_range(0.78, 0.9)
	step_audio.volume_db = 3.0 if state == CHASE else -1.0
	step_audio.play()


func _say(lines: Array) -> void:
	if _voice_cd > 0.0 or lines.is_empty():
		return
	_voice_cd = 4.0
	game.aunty_says(str(lines[randi() % lines.size()]))
