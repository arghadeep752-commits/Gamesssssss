extends Node3D
## The game: builds the house from the Blender map (res://assets/map/maze.glb) and its layout, spawns the
## player and Chaya, handles item pickups, the locked pooja room, the ritual and the jumpscare.

const GLB := "res://assets/map/maze.glb"
const GLTF := "res://assets/map/maze.gltf"
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
var tutorial := false
var found := {}
var _wisp: Node3D
var _wisp_light: OmniLight3D
var _wisp_target := Vector3.INF
var _wisp_path := PackedVector3Array()
var _wisp_repath := 0.0
var _wisp_hidden := false
var _tut_caught := false

func _ready() -> void:
	randomize()
	tutorial = Settings.tutorial
	Settings.tutorial = false
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
	elif tutorial:
		_tutorial.call_deferred()
	else:
		_intro_list.call_deferred()

func is_busy() -> bool:
	return caught_flag or ritual_flag

# ------------------------------------------------------------------------------------------ building

func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.36, 0.29, 0.25)
	env.ambient_light_energy = 0.45      # a little brighter (player request)
	env.fog_enabled = true
	env.fog_light_color = Color(0.03, 0.025, 0.025)
	env.fog_density = 0.038
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.1
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
				if nm.begins_with("scan_"):
					# real scanned objects keep their own photo textures from the model
					if mat is BaseMaterial3D:
						(mat as BaseMaterial3D).vertex_color_use_as_albedo = false
						(mat as BaseMaterial3D).texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
					continue
				mi.set_surface_override_material(i, Mats.get_material(nm))
	for c in n.get_children():
		_apply_mats(c)

func _build_map() -> void:
	var ps: PackedScene = load(GLTF if ResourceLoader.exists(GLTF) else GLB)
	map = ps.instantiate()
	add_child(map)
	_apply_mats(map)
	_setup_props(map)
	# furniture and lamps far away are hidden in the fog anyway: don't draw them (phone GPU)
	for node in map.get_children():
		var nn := String(node.name)
		for pre in ["prop_", "lamp_", "pedestal_", "painting_", "offering_", "pooja_vase", "pooja_lamp"]:
			if nn.begins_with(pre):
				for n in node.find_children("*", "MeshInstance3D", true, false):
					var gi := n as GeometryInstance3D
					gi.visibility_range_end = 21.0
					gi.visibility_range_end_margin = 2.0
				break
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
		pk.position = Vector3(it["pos"][0], it["pos"][1], it["pos"][2])      # before add_child: item.gd keeps this height
		add_child(pk)
		node.get_parent().remove_child(node)
		pk.add_child(node)
		node.transform = Transform3D.IDENTITY.scaled(Vector3.ONE * 1.25)      # a little bigger: easier to spot in the dark
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

func _setup_props(map: Node) -> void:
	# Blender-made furniture: textured wood/clay/brass with world-space (triplanar) mapping
	var tri := {}
	for node in map.get_children():
		if not String(node.name).begins_with("prop_"):
			continue
		for n in node.find_children("*", "MeshInstance3D", true, false):
			var mi := n as MeshInstance3D
			for i in range(mi.mesh.get_surface_count()):
				var m = mi.get_surface_override_material(i)
				if m is StandardMaterial3D and (m as StandardMaterial3D).albedo_texture != null:
					var key: int = m.get_instance_id()
					if not tri.has(key):
						var t := (m as StandardMaterial3D).duplicate() as StandardMaterial3D
						t.uv1_triplanar = true
						t.uv1_world_triplanar = true
						t.uv1_scale = Vector3.ONE * 1.4
						t.vertex_color_use_as_albedo = false
						tri[key] = t
					mi.set_surface_override_material(i, tri[key])

func _build_collisions() -> void:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	add_child(body)
	# furniture (props stand against walls, rotated in 90 degree steps)
	for pr in meta.get("props", []):
		var yaw := deg_to_rad(float(pr["yaw"]))
		var w := float(pr["size"][0])
		var d := float(pr["size"][1])
		var h := float(pr["h"])
		var back := float(pr.get("back", 0.45))
		var cx := float(pr.get("cx", 0.0))
		var c := Vector3(float(pr["pos"][0]), 0.0, float(pr["pos"][1])) + Basis(Vector3.UP, yaw) * Vector3(cx, h / 2.0, d / 2.0 - back)
		var sz := Vector3(w, h, d) if absf(sin(yaw)) < 0.5 else Vector3(d, h, w)
		_box(body, c, sz)
	# carved pillars and the stands the ritual items sit on
	for pl in meta.get("pillars", []):
		_box(body, Vector3(float(pl[0]), 1.4, float(pl[1])), Vector3(0.38, 2.8, 0.38))
	for it in meta["items"]:
		var ped: Array = it.get("ped", [0.56, 0.56])
		var pyaw := deg_to_rad(float(it.get("ped_yaw", 0.0)))
		var psz := Vector3(float(ped[0]), 0.74, float(ped[1])) if absf(sin(pyaw)) < 0.5 else Vector3(float(ped[1]), 0.74, float(ped[0]))
		_box(body, Vector3(float(it["pos"][0]), 0.37, float(it["pos"][2])), psz)
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
		o.light_energy = 2.3
		o.omni_range = 5.6
		o.omni_attenuation = 1.25
		o.distance_fade_enabled = true      # far lanterns are hidden by the fog anyway: skip them (phone GPU)
		o.distance_fade_begin = 13.0
		o.distance_fade_length = 3.0
		o.position = Vector3(l["pos"][0], l["pos"][1], l["pos"][2])
		add_child(o)
		lamps.append({"node": o, "base": 2.3, "ph": randf() * 20.0})
	# the brass lamps hanging in the pooja room
	for el in meta.get("extra_lights", []):
		var o2 := OmniLight3D.new()
		o2.light_color = Color(1.0, 0.6, 0.28)
		o2.light_energy = float(el[3])
		o2.omni_range = float(el[4])
		o2.omni_attenuation = 1.3
		o2.distance_fade_enabled = true
		o2.distance_fade_begin = 12.0
		o2.distance_fade_length = 3.0
		o2.position = Vector3(float(el[0]), float(el[1]), float(el[2]))
		add_child(o2)
		lamps.append({"node": o2, "base": float(el[3]), "ph": randf() * 20.0})

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
	found[String(pk.item_id)] = true
	pickups.erase(pk)
	pk.queue_free()
	var left := items_total - items_got
	if left > 0:
		hud.show_item_list(found, 2.6, "%s FOUND - %d MORE TO FIND" % [String(HudScript.ITEM_NAMES.get(String(pk.item_id), "ITEM")), left])
	if items_got >= items_total and not all_collected:
		all_collected = true
		_all_items_found()

func _intro_list() -> void:
	# the game starts: only the list of the six items to find for the ritual
	await get_tree().create_timer(1.2).timeout
	if not is_busy():
		hud.show_item_list(found, 6.5)

func _all_items_found() -> void:
	await get_tree().create_timer(1.2).timeout
	Sfx.play("bell", 0.0)
	if pooja_door:
		pooja_door.locked = false
	if not tutorial:
		ghost.enrage()
		hud.prompt("ALL ITEMS FOUND. TAKE THEM TO THE ALTAR IN THE POOJA ROOM", 4.5)
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
	if _wisp:
		_update_wisp(dt)
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
	if tutorial and not ritual_flag:
		_tut_caught = true
		Sfx.play("jumpscare", -6.0)
		player.add_shake(2.5)
		hud.flash = 0.7
		var tw := create_tween()
		tw.tween_property(hud, "flash", 0.0, 0.6)
		_tut_vanish()
		return
	if caught_flag or ritual_flag:
		return
	caught_flag = true
	player.frozen = true
	hud.reset_touches()
	hud.hide_controls()
	# 1. she is suddenly right in your face
	var dir := ghost.global_position - player.global_position
	dir.y = 0.0
	if dir.length() < 0.05:
		dir = -player.global_transform.basis.z
	dir = dir.normalized()
	ghost.global_position = player.global_position + dir * 0.95
	ghost.jumpscare_mode(player.global_position)
	await get_tree().process_frame
	var eye := player.global_position + Vector3(0, player.EYE_HEIGHT, 0)
	player.blackout = true                                  # the candle goes out
	for l in lamps:
		l["flick"] = 3.0                                    # every lamp in the house stutters
	Sfx.play("jumpscare", 6.0)
	Sfx.play("ritual_end", 4.0, 0.55)                       # deep boom under the scream
	Sfx.play("spotted", 1.0, 0.75)
	# harsh light from below her face, flashing
	var scare := OmniLight3D.new()
	scare.light_color = Color(1.0, 0.86, 0.8)
	scare.omni_range = 2.2
	scare.light_energy = 5.0
	add_child(scare)
	player.add_shake(4.5)
	hud.danger = 1.0
	var zoom := create_tween()
	zoom.tween_property(player.camera, "fov", 46.0, 0.17).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	var base_yaw: float = ghost.rotation.y
	var t := 0.0
	var next := 0.0
	var on := true
	while t < 1.6:
		await get_tree().process_frame
		var dt := get_process_delta_time()
		t += dt
		# the lunge: keep HER FACE (not her feet) on a line to the eye, rushing from 0.95 m to 0.33 m
		var k := clampf(t / 0.17, 0.0, 1.0)
		var d := lerpf(0.95, 0.33, 1.0 - pow(1.0 - k, 4.0))
		var off: Vector3 = ghost.face_center() - ghost.global_position
		off.y = 0.0
		ghost.global_position = player.global_position + dir * d - off
		var face: Vector3 = ghost.face_center()
		var to: Vector3 = face - eye
		player.face(rad_to_deg(atan2(-to.x, -to.z)), rad_to_deg(atan2(to.y, Vector2(to.x, to.z).length())))
		player.add_shake(3.0)
		scare.global_position = face + (eye - face).normalized() * 0.2 + Vector3(0, -0.18, 0)
		next -= dt
		if next <= 0.0:
			# strobe: her face flashes in and out of the dark, head jerking
			on = not on if randf() > 0.15 else true
			next = randf_range(0.035, 0.09)
			scare.light_energy = randf_range(4.5, 7.0) if on else 0.0
			ghost.rotation.y = base_yaw + randf_range(-0.12, 0.12)
			ghost.rotation.z = randf_range(-0.07, 0.07)
			hud.flash = randf_range(0.12, 0.3) if (on and randf() > 0.7) else 0.0
	# 3. black
	scare.light_energy = 0.0
	hud.flash = 0.0
	hud.fade = 1.0
	Sfx.play("heartbeat", -2.0)
	await get_tree().create_timer(1.6).timeout
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
	# the lamp is lit, at the tip of its cotton wick
	var fpos := diya_pos + Vector3(0, 0.09, 0)
	if item_models.has("diya"):
		var fa := (item_models["diya"] as Node3D).find_child("diya_flame_anchor", true, false) as Node3D
		if fa != null:
			fpos = fa.global_position
	var flame := MeshInstance3D.new()
	var fq := QuadMesh.new()
	fq.size = Vector2(0.026, 0.062)
	flame.mesh = fq
	var fmat := ShaderMaterial.new()
	fmat.shader = Shader.new()
	fmat.shader.code = PlayerScript.FLAME_SHADER
	flame.material_override = fmat
	flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(flame)
	flame.global_position = fpos + Vector3(0, 0.026, 0)
	var glow := MeshInstance3D.new()
	var gq := QuadMesh.new()
	gq.size = Vector2(0.17, 0.17)
	glow.mesh = gq
	var gmat := ShaderMaterial.new()
	gmat.shader = fmat.shader
	gmat.set_shader_parameter("glow", 1.0)
	glow.material_override = gmat
	glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(glow)
	glow.global_position = fpos + Vector3(0, 0.02, 0)
	var fl := OmniLight3D.new()
	fl.light_color = Color(1.0, 0.7, 0.35)
	fl.light_energy = 2.4
	fl.omni_range = 6.0
	add_child(fl)
	fl.global_position = fpos + Vector3(0, 0.25, 0)
	Sfx.loop_on("fire", self, -6.0)
	await get_tree().create_timer(2.5).timeout
	# Chaya comes to stop the ritual
	var spawn_at := maze.cell_center(Vector2i(int(L["pooja"]["door"]) % maze.cols, int(L["pooja"]["door"]) / maze.cols)) + Vector3(0, 0.05, 0)
	ghost.process_mode = Node.PROCESS_MODE_INHERIT
	ghost.visible = true
	_ghost_voice(true)
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
	if tutorial:
		hud.prompt("TUTORIAL COMPLETE! NOW PRESS START AND SURVIVE CHAYA'S HOUSE FOR REAL.")
		await get_tree().create_timer(4.0).timeout
	await get_tree().create_timer(1.2).timeout
	get_tree().change_scene_to_file(MENU)


# ------------------------------------------------------------------------------------------ the tutorial

func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout

func _ghost_voice(on: bool) -> void:
	var w = ghost.get("_whisper")
	if w is AudioStreamPlayer3D:
		(w as AudioStreamPlayer3D).stream_paused = not on

func _tutorial() -> void:
	ghost.active = false
	ghost.visible = false
	ghost.process_mode = Node.PROCESS_MODE_DISABLED
	_ghost_voice(false)
	await _wait(1.5)
	hud.prompt("WELCOME TO CHAYA'S HOUSE. THIS TUTORIAL TEACHES YOU HOW TO PLAY.", 3.4)
	await _wait(4.0)
	# walking
	hud.prompt("MOVE: PUT YOUR THUMB ON THE LEFT SIDE OF THE SCREEN AND DRAG IT")
	hud.highlight = "joy"
	var start := player.global_position
	while player.global_position.distance_to(start) < 2.4:
		await get_tree().process_frame
	hud.highlight = ""
	Sfx.play("pickup", -12.0, 1.5)
	# looking
	hud.prompt("LOOK AROUND: SWIPE ON THE RIGHT SIDE OF THE SCREEN")
	hud.highlight = "look"
	var turned := 0.0
	var ly: float = player.yaw
	var lp: float = player.pitch
	while turned < 110.0:
		await get_tree().process_frame
		turned += absf(player.yaw - ly) + absf(player.pitch - lp)
		ly = player.yaw
		lp = player.pitch
	hud.highlight = ""
	Sfx.play("pickup", -12.0, 1.5)
	# running
	hud.prompt("RUN: KEEP MOVING AND HOLD THE RUNNING BUTTON")
	hud.highlight = "run"
	var ran := 0.0
	while ran < 1.2:
		await get_tree().process_frame
		if player.running:
			ran += get_process_delta_time()
	hud.highlight = ""
	Sfx.play("pickup", -12.0, 1.5)
	hud.prompt("RUNNING IS FAST BUT LOUD. CHAYA CAN HEAR YOUR FOOTSTEPS.", 3.6)
	await _wait(4.2)
	# the goal
	hud.show_item_list(found, 0.0, "FIND THESE SIX HOLY ITEMS FOR THE RITUAL")
	hud.prompt("PUT ALL SIX ON THE ALTAR OF THE POOJA ROOM TO DESTROY CHAYA FOR EVER", 5.0)
	await _wait(5.6)
	hud.hide_item_list()
	hud.prompt("FOLLOW THE LIGHT. DOORS OPEN BY THEMSELVES WHEN YOU WALK UP TO THEM. WALK INTO AN ITEM TO PICK IT UP.", 6.0)
	_wisp_on()
	while items_got < 2:
		await get_tree().process_frame
	await _wait(2.8)
	await _tut_chase_lesson()
	while not all_collected:
		await get_tree().process_frame
	await _wait(1.4)
	hud.prompt("ALL SIX FOUND! THE POOJA ROOM DOOR IS OPEN NOW. FOLLOW THE LIGHT TO THE ALTAR.", 5.5)
	while not ritual_flag:
		await get_tree().process_frame
	_wisp_off()
	hud.prompt("THE RITUAL BEGINS... STAY AT THE ALTAR!", 4.0)

func _tut_chase_lesson() -> void:
	_wisp_hidden = true
	hud.prompt("CAREFUL! CHAYA IS AWAKE. WHEN THE SCREEN TURNS RED AND YOU HEAR YOUR HEART BEAT, SHE IS CLOSE.", 5.0)
	# she appears a few rooms away and comes for you
	var best := Vector2i(-1, -1)
	var bd := 999
	for c in maze.open_cells:
		var n := maze.path(player.global_position, maze.cell_center(c)).size()
		if n >= 4 and absi(n - 6) < bd:
			bd = absi(n - 6)
			best = c
	if best.x < 0:
		best = Vector2i(int(L["ghost_cell"][0]), int(L["ghost_cell"][1]))
	ghost.process_mode = Node.PROCESS_MODE_INHERIT
	ghost.visible = true
	_ghost_voice(true)
	ghost.warp_to(maze.cell_center(best) + Vector3(0, 0.05, 0))
	ghost.active = true
	ghost.state = ghost.S.HEARD
	ghost._set_target(player.global_position)
	_tut_caught = false
	await _wait(5.2)
	if not _tut_caught:
		hud.prompt("RUN! KEEP AWAY FROM HER AND BREAK HER LINE OF SIGHT", 3.5)
	var t := 0.0
	var re := 0.0
	while t < 15.0 and not _tut_caught:
		await get_tree().process_frame
		var dt := get_process_delta_time()
		t += dt
		re -= dt
		if re <= 0.0 and ghost.state != ghost.S.CHASE and ghost.active:
			re = 2.0
			ghost.state = ghost.S.HEARD
			ghost._set_target(player.global_position)
	if _tut_caught:
		hud.prompt("SHE CAUGHT YOU! IN THE REAL GAME THAT MEANS GAME OVER. RUN, AND HIDE BEHIND DOORS AND CORNERS.", 6.0)
	else:
		_tut_vanish()
		hud.prompt("YOU GOT AWAY! WHEN SHE LOSES YOU, SHE GOES BACK TO WANDERING THE HOUSE.", 5.0)
	await _wait(6.4)
	hud.prompt("NOW FIND THE REST OF THE ITEMS. FOLLOW THE LIGHT.", 4.0)
	_wisp_hidden = false

func _tut_vanish() -> void:
	ghost.active = false
	ghost.velocity = Vector3.ZERO
	ghost.state = ghost.S.PATROL
	ghost.visible = false
	ghost.warp_to(maze.cell_center(Vector2i(int(L["ghost_cell"][0]), int(L["ghost_cell"][1]))) + Vector3(0, 0.05, 0))
	ghost.set_deferred("process_mode", Node.PROCESS_MODE_DISABLED)
	_ghost_voice(false)
	var tw := create_tween()
	tw.tween_property(hud, "danger", 0.0, 0.8)

func _wisp_on() -> void:
	if _wisp:
		return
	_wisp = Node3D.new()
	add_child(_wisp)
	var sh := Shader.new()
	sh.code = PlayerScript.FLAME_SHADER
	for sz in [0.62, 0.2]:
		var q := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(sz, sz)
		q.mesh = qm
		var m := ShaderMaterial.new()
		m.shader = sh
		m.set_shader_parameter("glow", 1.0)
		q.material_override = m
		q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_wisp.add_child(q)
	_wisp_light = OmniLight3D.new()
	_wisp_light.light_color = Color(1.0, 0.78, 0.45)
	_wisp_light.light_energy = 1.4
	_wisp_light.omni_range = 4.0
	_wisp.add_child(_wisp_light)
	_wisp.global_position = player.global_position + Vector3(0, 1.4, 0) - player.global_transform.basis.z * 1.5
	hud.guide_on = true

func _wisp_off() -> void:
	if _wisp:
		_wisp.queue_free()
		_wisp = null
	hud.guide_on = false

func _update_wisp(dt: float) -> void:
	_wisp.visible = not _wisp_hidden
	hud.guide_on = not _wisp_hidden
	if _wisp_hidden:
		return
	# the target: the nearest item still to find, then the altar
	var target := altar_pos
	if not all_collected:
		var bestd := 1e9
		for pk in pickups:
			var dd: float = (pk as Node3D).global_position.distance_to(player.global_position)
			if dd < bestd:
				bestd = dd
				target = (pk as Node3D).global_position
	_wisp_repath -= dt
	if _wisp_repath <= 0.0:
		_wisp_repath = 0.4
		_wisp_path = maze.path(player.global_position, target)
	# a point about 2.4 m ahead of the player along the way
	var pts := PackedVector3Array([Vector3(player.global_position.x, 0, player.global_position.z)])
	for p in _wisp_path:
		pts.append(p)
	pts.append(Vector3(target.x, 0, target.z))
	var want := Vector3(target.x, target.y + 0.55, target.z)
	var left := 2.4
	for i in range(pts.size() - 1):
		var seg := pts[i + 1] - pts[i]
		var ln := seg.length()
		if ln >= left:
			var p2 := pts[i] + seg * (left / maxf(ln, 0.001))
			want = Vector3(p2.x, 1.35, p2.z)
			break
		left -= ln
	want.y += sin(_t * 2.3) * 0.08
	_wisp.global_position = _wisp.global_position.lerp(want, clampf(dt * 2.6, 0.0, 1.0))
	_wisp_light.light_energy = 1.3 + 0.2 * sin(_t * 7.0)
	var cam: Camera3D = player.camera
	var wp := _wisp.global_position
	var vs := get_viewport().get_visible_rect().size
	var sp := cam.unproject_position(wp)
	var behind := cam.is_position_behind(wp)
	if behind:
		sp = vs / 2.0 - (sp - vs / 2.0) * 10.0
	hud.guide_screen = sp
	hud.guide_visible = (not behind) and Rect2(Vector2(60, 60), vs - Vector2(120, 120)).has_point(sp)

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
		hud.show_item_list(found, 0.0)
		await get_tree().create_timer(0.7).timeout
		await _snap("%02d_item_list" % n); n += 1
		found["kalash"] = true
		found["diya"] = true
		hud.show_item_list(found, 0.0, "DIYA FOUND - 4 MORE TO FIND")
		await get_tree().create_timer(0.7).timeout
		await _snap("%02d_item_list_found" % n); n += 1
		found.clear()
		hud.hide_item_list()
		hud.prompt("MOVE: PUT YOUR THUMB ON THE LEFT SIDE OF THE SCREEN AND DRAG IT")
		hud.highlight = "joy"
		await get_tree().create_timer(0.7).timeout
		await _snap("%02d_tutorial" % n); n += 1
		hud.highlight = ""
		hud.hide_prompt()
		await get_tree().create_timer(0.6).timeout
		_place(Vector3(sp[0], 0.05, sp[1]), 180.0, -6.0)
		await _snap("%02d_front_door" % n); n += 1
	# a corridor and a room: pick cells
	var shots := [[Vector2i(7, 8), 0.0], [Vector2i(3, 2), 90.0], [Vector2i(10, 1), 200.0], [Vector2i(13, 8), 270.0]]
	for s in shots:
		if only_ghost:
			break
		_place(maze.cell_center(s[0]) + Vector3(0, 0.05, 0), s[1])
		await _snap("%02d_cell_%d_%d" % [n, s[0].x, s[0].y]); n += 1
	# every ritual item on its pedestal, close up (the tour must not pick them up)
	for pk in pickups:
		pk.player = null
	if not only_ghost:
		for it in meta["items"]:
			var p := Vector3(it["pos"][0], 0.05, it["pos"][2])
			var best := Vector3.ZERO
			for off in [Vector3(0.85, 0, 0), Vector3(-0.85, 0, 0), Vector3(0, 0, 0.85), Vector3(0, 0, -0.85)]:
				if maze.world_to_cell(p + off) == maze.world_to_cell(p):
					best = off
					break
			var yaw := rad_to_deg(atan2(best.x, best.z))
			var drop: float = float(it["pos"][1]) + 0.22 - (0.05 + player.EYE_HEIGHT)
			_place(p + best, yaw, rad_to_deg(atan2(drop, maxf(0.3, best.length()))))
			await _snap("%02d_item_%s" % [n, it["id"]]); n += 1
	# the scanned furniture, a pillar, a painting, a lantern
	if not only_ghost:
		var props: Array = meta.get("props", [])
		for k in range(mini(props.size(), 10)):
			var pr: Dictionary = props[k]
			var yaw := deg_to_rad(float(pr["yaw"]))
			var b := Basis(Vector3.UP, yaw)
			var c := Vector3(float(pr["pos"][0]), 0.0, float(pr["pos"][1])) + b * Vector3(float(pr.get("cx", 0.0)), 0.0, 0.0)
			var eye := c + b * Vector3(0.35, 0.0, 2.1)
			var look := c + Vector3(0, minf(float(pr["h"]) * 0.5, 0.9), 0) - (eye + Vector3(0, 0.05 + player.EYE_HEIGHT, 0))
			_place(eye + Vector3(0, 0.05, 0), rad_to_deg(atan2(-look.x, -look.z)), rad_to_deg(atan2(look.y, Vector2(look.x, look.z).length())))
			await _snap("%02d_prop_%s" % [n, String(pr["kind"])]); n += 1
		var pls: Array = meta.get("pillars", [])
		if pls.size() > 0:
			var pc := Vector3(float(pls[0][0]), 0.0, float(pls[0][1]))
			var e2 := pc + Vector3(1.6, 0, 1.1)
			var lk := pc + Vector3(0, 1.6, 0) - (e2 + Vector3(0, 1.63, 0))
			_place(e2 + Vector3(0, 0.05, 0), rad_to_deg(atan2(-lk.x, -lk.z)), rad_to_deg(atan2(lk.y, Vector2(lk.x, lk.z).length())))
			await _snap("%02d_pillar" % n); n += 1
		var pts: Array = meta.get("paintings", [])
		if pts.size() > 0:
			var fp := Vector3(float(pts[0]["pos"][0]), 0.0, float(pts[0]["pos"][2]))
			var nn := Vector3(float(pts[0]["n"][0]), 0.0, float(pts[0]["n"][1]))
			var e3 := fp + nn * 1.7
			_place(e3 + Vector3(0, 0.05, 0), rad_to_deg(atan2(nn.x, nn.z)), 4.0)
			await _snap("%02d_painting" % n); n += 1
		var lt: Array = L["lights"]
		if lt.size() > 0:
			var lpos := Vector3(float(lt[0]["pos"][0]), 0.0, float(lt[0]["pos"][2]))
			_place(lpos + Vector3(0, 0.05, 1.5), 0.0, 30.0)
			await _snap("%02d_lantern" % n); n += 1
		# the pooja room
		var pc2 := Vector3(float(L["pooja"]["center"][0]), 0.0, float(L["pooja"]["center"][1]))
		_place(pc2 + Vector3(0, 0.05, 2.9), 0.0, -14.0)
		await _snap("%02d_pooja" % n); n += 1
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
	# each of her motions, caught mid-move (Mixamo clips once the developer has added them)
	player.face(0.0, -4.0)
	ghost.global_position = base + Vector3(0, 0.05, -2.6)
	print("[CHAYA-TEST] mixamo clips: ", ghost.mixamo_clips)
	for key in ["idle", "walk", "run", "scream", "attack"]:
		if ghost.anim != null and ghost.anim.has_animation("c/" + key):
			ghost._anim_name = ""
			ghost._play(key, 1.0)
			ghost.anim.seek(ghost.anim.get_animation("c/" + key).length * 0.35, true)
			await _snap("%02d_pose_%s" % [n, key]); n += 1
	print("[CHAYA-TEST] DONE")
	get_tree().quit()
