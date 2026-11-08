extends Node3D
## The game: builds the house from the Blender map (res://assets/map/maze.glb) and its layout, spawns the
## player and Chaya, handles item pickups, the locked pooja room, the ritual and the jumpscare.

const GLB := "res://assets/map/maze.glb"
const MENU := "res://game/menu.tscn"
const PlayerScript := preload("res://game/scripts/player.gd")
const GhostScript := preload("res://game/scripts/ghost.gd")
const HudScript := preload("res://game/scripts/hud.gd")
const DoorScript := preload("res://game/scripts/door.gd")
const ItemScript := preload("res://game/scripts/item.gd")

var maze: MazeData
var meta: Dictionary
var L: Dictionary
var player: CharacterBody3D
var ghost: CharacterBody3D
var hud: CanvasLayer
var map: Node3D
var doors: Array = []
var pooja_door: Node3D
var pickups: Array = []
var item_models := {}
var items_total := 0
var items_got := 0
var altar_pos := Vector3.ZERO
var lamps: Array = []
var caught_flag := false
var ritual_flag := false
var all_collected := false
var _t := 0.0
var _danger := 0.0
var _heart: Node
var _ambience_t := 12.0
var _perf_t := 0.0
var _perf_n := 0
var _perf_sum := 0.0
var _perf_stage := 0

func _ready() -> void:
	randomize()
	maze = MazeData.load_layout()
	L = maze.L
	meta = JSON.parse_string(FileAccess.get_file_as_string("res://assets/map/meta.json"))
	_build_environment()
	_build_map()
	_build_collisions()
	_build_lights()
	_spawn_player()
	_spawn_ghost()
	_build_hud()
	Sfx.loop_on("ambient", self, -7.0)
	_heart = Sfx.loop_on("heartbeat", self, -60.0)
	hud.fade = 1.0
	var tw := create_tween()
	tw.tween_property(hud, "fade", 0.0, 1.6)
	if OS.get_environment("CHAYA_SHOTS") != "":
		_shots_tour.call_deferred()

func is_busy() -> bool:
	return caught_flag or ritual_flag

# ------------------------------------------------------------------------------------------ building

func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.32, 0.26, 0.24)
	env.ambient_light_energy = 0.22
	env.fog_enabled = true
	env.fog_light_color = Color(0.03, 0.025, 0.025)
	env.fog_density = 0.05
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.0
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.1
	env.adjustment_saturation = 0.88
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

func _apply_mats(n: Node) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if mi.mesh:
			for i in range(mi.mesh.get_surface_count()):
				var mat := mi.mesh.surface_get_material(i)
				var nm := mat.resource_name if mat else ""
				mi.set_surface_override_material(i, Mats.get_material(nm))
	for c in n.get_children():
		_apply_mats(c)

func _build_map() -> void:
	var ps: PackedScene = load(GLB)
	map = ps.instantiate()
	add_child(map)
	_apply_mats(map)
	# doors
	for info in meta["doors"]:
		var node := map.find_child(info["name"], true, false)
		if node != null:
			_make_door(info, node)
	# ritual items
	for it in meta["items"]:
		var node := map.find_child(it["name"], true, false)
		if node == null:
			continue
		var pk := Node3D.new()
		pk.set_script(ItemScript)
		pk.item_id = it["id"]
		pk.player = player
		add_child(pk)
		pk.global_position = Vector3(it["pos"][0], it["pos"][1], it["pos"][2])
		node.get_parent().remove_child(node)
		pk.add_child(node)
		node.transform = Transform3D.IDENTITY
		item_models[it["id"]] = node.duplicate()
		pk.collected.connect(_on_item_collected)
		pickups.append(pk)
	items_total = pickups.size()
	altar_pos = Vector3(meta["altar"]["pos"][0], meta["altar"]["pos"][1], meta["altar"]["pos"][2])

func _make_door(info: Dictionary, node: Node3D) -> void:
	var hinge := Vector3(info["hinge"][0], 0.0, info["hinge"][2])
	var pivot := Node3D.new()
	pivot.set_script(DoorScript)
	add_child(pivot)
	pivot.global_position = hinge
	node.get_parent().remove_child(node)
	pivot.add_child(node)
	node.transform = Transform3D.IDENTITY
	var horizontal: bool = info["o"] == "h"
	var sgn := float(info["sgn"])
	pivot.leaf_dir = Vector3(sgn, 0, 0) if horizontal else Vector3(0, 0, sgn)
	pivot.plane_n = Vector3(0, 0, 1) if horizontal else Vector3(1, 0, 0)
	var w := float(info["width"])
	var h := float(info["height"])
	var th := float(info["thick"])
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(w, h, th) if horizontal else Vector3(th, h, w)
	cs.shape = bs
	cs.position = pivot.leaf_dir * (w / 2.0) + Vector3(0, h / 2.0, 0)
	body.add_child(cs)
	pivot.add_child(body)
	if info["kind"] == "pooja":
		pivot.locked = true
		pivot.reach = 2.2
		pooja_door = pivot
	doors.append(pivot)

func _box(parent: StaticBody3D, center: Vector3, size: Vector3) -> void:
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	cs.position = center
	parent.add_child(cs)

func _build_collisions() -> void:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	add_child(body)
	var T := float(L["wall_t"])
	var H := float(L["wall_h"])
	var S := float(L["cell"])
	for w in L["walls"]:
		var a := float(w["a"]) - T / 2.0
		var b := float(w["b"]) + T / 2.0
		var p := float(w["p"])
		if w["o"] == "h":
			_box(body, Vector3((a + b) / 2.0, H / 2.0, p), Vector3(b - a, H, T))
		else:
			_box(body, Vector3(p, H / 2.0, (a + b) / 2.0), Vector3(T, H, b - a))
	var DW := float(L["door_w"])
	for d in L["doorways"]:
		var ow := DW
		if d["kind"] == "arch":
			ow = DW + 0.45
		elif d["kind"] == "pooja":
			ow = DW + 0.3
		var c := float(d["c"])
		var p := float(d["p"])
		for seg in [[c - S / 2.0 - T / 2.0, c - ow / 2.0], [c + ow / 2.0, c + S / 2.0 + T / 2.0]]:
			var a := float(seg[0])
			var b := float(seg[1])
			if d["o"] == "h":
				_box(body, Vector3((a + b) / 2.0, H / 2.0, p), Vector3(b - a, H, T))
			else:
				_box(body, Vector3(p, H / 2.0, (a + b) / 2.0), Vector3(T, H, b - a))
	var W := float(L["cols"]) * S
	var D := float(L["rows"]) * S
	_box(body, Vector3(0, -0.5, 0), Vector3(W + 6.0, 1.0, D + 6.0))
	# the altar
	_box(body, Vector3(altar_pos.x, 0.25, altar_pos.z), Vector3(1.2, 0.5, 1.2))
	_box(body, Vector3(altar_pos.x, 0.09, altar_pos.z), Vector3(2.0, 0.18, 2.0))

func _build_lights() -> void:
	for l in L["lights"]:
		var o := OmniLight3D.new()
		o.light_color = Color(1.0, 0.62, 0.3)
		o.light_energy = 1.7
		o.omni_range = 4.8
		o.omni_attenuation = 1.25
		o.position = Vector3(l["pos"][0], l["pos"][1], l["pos"][2])
		add_child(o)
		lamps.append({"node": o, "base": 1.7, "ph": randf() * 20.0})

func _spawn_player() -> void:
	player = CharacterBody3D.new()
	player.set_script(PlayerScript)
	add_child(player)
	var sp: Array = L["spawn"]["pos"]
	player.global_position = Vector3(sp[0], 0.05, sp[1])
	player.yaw = float(L["spawn"]["yaw"])
	for pk in pickups:
		pk.player = player

func _spawn_ghost() -> void:
	ghost = CharacterBody3D.new()
	ghost.set_script(GhostScript)
	add_child(ghost)
	var gc := Vector2i(int(L["ghost_cell"][0]), int(L["ghost_cell"][1]))
	ghost.global_position = maze.cell_center(gc) + Vector3(0, 0.05, 0)
	ghost.setup(self, maze, player)
	ghost.caught_player.connect(_on_caught)
	for d in doors:
		d.actors = [player, ghost]

func _build_hud() -> void:
	hud = CanvasLayer.new()
	hud.set_script(HudScript)
	add_child(hud)
	hud.look.connect(player.look_delta)
	player.hud = hud

# ------------------------------------------------------------------------------------------ gameplay

func ghost_spotted() -> void:
	player.add_shake(0.8)
	Sfx.play("spotted", -2.0)

func _on_item_collected(pk: Node3D) -> void:
	items_got += 1
	Sfx.play("pickup", -2.0)
	pickups.erase(pk)
	pk.queue_free()
	if items_got >= items_total and not all_collected:
		all_collected = true
		_all_items_found()

func _all_items_found() -> void:
	await get_tree().create_timer(1.2).timeout
	Sfx.play("bell", 0.0)
	if pooja_door:
		pooja_door.locked = false
	ghost.enrage()
	player.flicker_light(2.5)
	for l in lamps:
		l["flick"] = 3.0

func _process(dt: float) -> void:
	_t += dt
	# lantern flicker
	for l in lamps:
		var o: OmniLight3D = l["node"]
		var ph: float = l["ph"]
		var f := 0.88 + 0.08 * sin(_t * 9.0 + ph) + 0.05 * sin(_t * 23.0 + ph * 2.0)
		if l.has("flick") and l["flick"] > 0.0:
			l["flick"] -= dt
			f *= 0.2 + 0.8 * float(randf() > 0.5)
		o.light_energy = float(l["base"]) * f
	if ghost and not caught_flag:
		var d := ghost.global_position.distance_to(player.global_position)
		var chasing: bool = ghost.state == ghost.S.CHASE
		var want := 1.0 if chasing else clampf(1.0 - d / 9.0, 0.0, 0.5)
		_danger = lerpf(_danger, want, clampf(dt * 2.0, 0.0, 1.0))
		hud.danger = _danger
		if _heart is AudioStreamPlayer:
			(_heart as AudioStreamPlayer).volume_db = lerpf(-60.0, -2.0, clampf(_danger * 1.4, 0.0, 1.0))
		if d < 6.5 and not ritual_flag:
			if randf() < dt * 2.5:
				player.flicker_light(0.25)
			for l in lamps:
				var lp: Vector3 = (l["node"] as Node3D).global_position
				if lp.distance_to(ghost.global_position) < 5.0:
					l["flick"] = 0.3
		if chasing:
			player.add_shake(0.25)
	# ambience
	_ambience_t -= dt
	if _ambience_t <= 0.0 and not is_busy():
		_ambience_t = randf_range(14.0, 32.0)
		var ang := randf() * TAU
		var pos := player.global_position + Vector3(cos(ang), 1.2, sin(ang)) * randf_range(6.0, 12.0)
		var snd: String = ["creak", "whisper_far", "knock", "distant_cry"][randi() % 4]
		Sfx.play_at(snd, self, pos, 0.0, randf_range(0.85, 1.1), 28.0)
	# the altar
	if all_collected and not ritual_flag and not caught_flag:
		var dd := player.global_position - altar_pos
		dd.y = 0.0
		if dd.length() < 1.95:
			_start_ritual()
	_perf_monitor(dt)

func _perf_monitor(dt: float) -> void:
	_perf_t += dt
	if _perf_t < 3.0 or _perf_stage >= 2:
		return
	_perf_sum += dt
	_perf_n += 1
	if _perf_sum >= 4.0:
		var fps := float(_perf_n) / _perf_sum
		_perf_sum = 0.0
		_perf_n = 0
		if fps < 24.0:
			_perf_stage += 1
			if _perf_stage == 1:
				player.flashlight.shadow_enabled = false
			else:
				get_viewport().msaa_3d = Viewport.MSAA_DISABLED
		else:
			_perf_stage = 2

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		get_tree().change_scene_to_file(MENU)

# ------------------------------------------------------------------------------------------ caught

func _on_caught() -> void:
	if caught_flag or ritual_flag:
		return
	caught_flag = true
	player.frozen = true
	hud.reset_touches()
	var to := ghost.global_position + Vector3(0, 1.55, 0) - (player.global_position + Vector3(0, player.EYE_HEIGHT, 0))
	var yaw := rad_to_deg(atan2(-to.x, -to.z))
	var pitch := rad_to_deg(atan2(to.y, Vector2(to.x, to.z).length()))
	player.face(yaw, pitch)
	player.flashlight.light_energy = 6.0
	player.add_shake(3.0)
	Sfx.play("jumpscare", 4.0)
	hud.flash = 0.0
	var tw := create_tween()
	tw.tween_property(player.camera, "fov", 44.0, 0.25)
	hud.danger = 1.0
	await get_tree().create_timer(0.1).timeout
	player.flicker_light(2.0)
	await get_tree().create_timer(1.7).timeout
	var tf := create_tween()
	tf.tween_property(hud, "fade", 1.0, 0.7)
	await tf.finished
	await get_tree().create_timer(0.5).timeout
	get_tree().change_scene_to_file(MENU)

# ------------------------------------------------------------------------------------------ the ritual

func _start_ritual() -> void:
	ritual_flag = true
	player.frozen = true
	hud.reset_touches()
	Sfx.play("bell", 0.0)
	var altar_c := altar_pos + Vector3(0, 0.3, 0)
	var to := altar_c - (player.global_position + Vector3(0, player.EYE_HEIGHT, 0))
	var tw := create_tween().set_parallel(true)
	tw.tween_property(player, "yaw", rad_to_deg(atan2(-to.x, -to.z)), 1.2)
	tw.tween_property(player, "pitch", rad_to_deg(atan2(to.y, Vector2(to.x, to.z).length())) - 4.0, 1.2)
	Sfx.loop_on("ritual_chant", self, -2.0)
	# the six items appear on the altar
	var ids: Array = item_models.keys()
	var diya_pos := altar_pos
	for k in range(ids.size()):
		var m: Node3D = item_models[ids[k]]
		add_child(m)
		var ang := TAU * float(k) / float(ids.size())
		var p := altar_pos + Vector3(cos(ang), 0.0, sin(ang)) * 0.42
		if ids[k] == "diya":
			p = altar_pos + Vector3(0, 0.0, 0.0)
			diya_pos = p
		m.global_position = p
		await get_tree().create_timer(0.35).timeout
		Sfx.play("pickup", -6.0, 0.8 + 0.05 * k)
	# the lamp is lit
	var flame := MeshInstance3D.new()
	var fm := SphereMesh.new()
	fm.radius = 0.022
	fm.height = 0.08
	flame.mesh = fm
	var fmat := StandardMaterial3D.new()
	fmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fmat.albedo_color = Color(1.0, 0.75, 0.25)
	flame.material_override = fmat
	add_child(flame)
	flame.global_position = diya_pos + Vector3(0, 0.09, 0)
	var fl := OmniLight3D.new()
	fl.light_color = Color(1.0, 0.7, 0.35)
	fl.light_energy = 2.4
	fl.omni_range = 6.0
	add_child(fl)
	fl.global_position = diya_pos + Vector3(0, 0.35, 0)
	Sfx.loop_on("fire", self, -6.0)
	await get_tree().create_timer(2.5).timeout
	# Chaya comes to stop the ritual
	var spawn_at := maze.cell_center(Vector2i(int(L["pooja"]["door"]) % maze.cols, int(L["pooja"]["door"]) / maze.cols)) + Vector3(0, 0.05, 0)
	ghost.warp_to(spawn_at)
	ghost.active = true
	ghost.start_ritual_mode()
	Sfx.play("jumpscare", 0.0, 0.8)
	player.add_shake(1.5)
	hud.danger = 1.0
	player.flicker_light(3.0)
	for l in lamps:
		l["flick"] = 6.0
	var t := 0.0
	while t < 6.0:
		await get_tree().process_frame
		var dt := get_process_delta_time()
		t += dt
		fl.light_energy = 2.2 + sin(_t * 17.0) * 0.4
		flame.scale = Vector3(1, 1.0 + 0.3 * sin(_t * 21.0), 1)
		player.add_shake(0.6)
		if ghost.global_position.distance_to(player.global_position) < 1.8:
			ghost.velocity = Vector3.ZERO
			ghost.active = false
		if t > 2.0 and t < 5.0:
			pass
	# the ritual is complete: she is destroyed forever
	Sfx.play("ritual_end", 2.0)
	var df := create_tween()
	df.tween_property(hud, "flash", 1.0, 0.9)
	await df.finished
	ghost.active = false
	ghost.visible = false
	var dd := create_tween()
	dd.tween_property(hud, "danger", 0.0, 0.5)
	await get_tree().create_timer(1.6).timeout
	var fo := create_tween()
	fo.tween_property(hud, "fade", 1.0, 2.0)
	await fo.finished
	await get_tree().create_timer(1.2).timeout
	get_tree().change_scene_to_file(MENU)

# ------------------------------------------------------------------------------------------ screenshot tour (build checks)

func _snap(file: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := OS.get_environment("CHAYA_SHOTS")
	DirAccess.make_dir_recursive_absolute(dir)
	img.save_png(dir.path_join(file + ".png"))
	print("[CHAYA-TEST] snap ", file, " ", img.get_size())

func _place(pos: Vector3, yaw: float, pitch := 0.0) -> void:
	player.global_position = pos
	player.face(yaw, pitch)
	player.velocity = Vector3.ZERO

func _shots_tour() -> void:
	player.frozen = true
	ghost.active = false
	hud.fade = 0.0
	await get_tree().create_timer(1.0).timeout
	var sp: Array = L["spawn"]["pos"]
	var n := 1
	var only_ghost := OS.get_environment("CHAYA_SHOTS_ONLY") == "ghost"
	if not only_ghost:
		_place(Vector3(sp[0], 0.05, sp[1]), 0.0)
		await _snap("%02d_spawn" % n); n += 1
	# a corridor and a room: pick cells
	var shots := [[Vector2i(7, 8), 0.0], [Vector2i(3, 2), 90.0], [Vector2i(10, 1), 200.0], [Vector2i(13, 8), 270.0]]
	for s in shots:
		if only_ghost:
			break
		_place(maze.cell_center(s[0]) + Vector3(0, 0.05, 0), s[1])
		await _snap("%02d_cell_%d_%d" % [n, s[0].x, s[0].y]); n += 1
	# an item on its pedestal
	if meta["items"].size() > 0 and not only_ghost:
		var it: Dictionary = meta["items"][0]
		var p := Vector3(it["pos"][0], 0.05, it["pos"][2])
		var best := Vector3.ZERO
		for off in [Vector3(1.4, 0, 0), Vector3(-1.4, 0, 0), Vector3(0, 0, 1.4), Vector3(0, 0, -1.4)]:
			if maze.world_to_cell(p + off) == maze.world_to_cell(p):
				best = off
				break
		var yaw := rad_to_deg(atan2(best.x, best.z))
		_place(p + best, yaw, -22.0)
		await _snap("%02d_item" % n); n += 1
	# Chaya in front of the camera
	var base := maze.cell_center(Vector2i(7, 8))
	_place(base + Vector3(0, 0.05, 0), 0.0)
	ghost.global_position = base + Vector3(0, 0.05, -3.2)
	ghost.rotation.y = PI
	ghost._yaw = PI
	await _snap("%02d_chaya_far" % n); n += 1
	ghost.global_position = base + Vector3(0, 0.05, -1.7)
	await _snap("%02d_chaya_near" % n); n += 1
	print("[CHAYA-TEST] hair_root ", ghost.hair_root.global_position, " eye ", ghost._eye_glow[0].global_position, " eyeL ", ghost._eye_glow[1].global_position, " visual ", ghost.visual.global_position, " ghost ", ghost.global_position, " head bone ", ghost.skel.global_transform * ghost.skel.get_bone_global_pose(ghost._head).origin)
	player.face(0.0, 8.0)
	ghost.global_position = base + Vector3(0, 0.05, -1.05)
	await _snap("%02d_chaya_face" % n); n += 1
	print("[CHAYA-TEST] DONE")
	get_tree().quit()
