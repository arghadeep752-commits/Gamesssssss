class_name Game
extends Node3D
## Starts everything, runs the game's states, cheats and saving.

enum S { LOADING, MENU, PLAY, PAUSED, DEAD }

const CHEAT_LIST := "CHEAT CODES\nDial them in the Cheats app.\n\n" + \
	"1999  Full health and armour\n4545  Get ₹1,00,000\n1122  All weapons and ammo\n0000  Clear wanted level\n7777  Five stars\n" + \
	"4321  Never wanted (on / off)\n1100  God mode (on / off)\n1001  Super run (on / off)\n1234  Moon gravity (on / off)\n" + \
	"8080  Sports car\n2323  Motorbike\n6060  Auto rickshaw\n1515  Bus\n3030  Police jeep\n9090  Helicopter\n5050  Speedboat\n" + \
	"6000  Skip 6 hours\n2222  Blow up nearby vehicles\n3131  Go home\n"

var state := S.LOADING
var settings := {"quality": 1, "distance": 1, "density": 1, "sound": 8, "music": 6, "sens": 5, "fps": 0}
var save := {}
var god_mode := false
var models
var world: Node3D
var city
var env
var hud: Hud
var menus: Menus
var ui_root: Control
var loading: Control
var load_text: Label
var orbit_centre := Vector3.ZERO
var point_vehicles := {}          # point index -> Vehicle
var markers: Array[MeshInstance3D] = []
var next_point_check := 0.0
var edge_toast := 0.0


func _ready() -> void:
	G.game = self
	Engine.max_fps = 60
	process_mode = Node.PROCESS_MODE_ALWAYS
	load_settings()
	Ui.init_fonts()
	var layer := CanvasLayer.new()
	layer.layer = 10
	layer.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(layer)
	ui_root = Control.new()
	ui_root.name = "UI"
	ui_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_root.process_mode = Node.PROCESS_MODE_ALWAYS
	layer.add_child(ui_root)
	ui_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	Ui.root = ui_root
	show_loading()
	await get_tree().process_frame
	await get_tree().process_frame
	step("Loading Agartala...")
	await get_tree().process_frame
	world = Node3D.new()
	world.name = "World"
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	env = preload("res://scripts/env.gd").new()
	env.name = "Env"
	env.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(env)
	G.env = env
	env.setup(world)
	models = preload("res://scripts/models.gd").new()
	models.init_models()
	city = preload("res://scripts/city.gd").new()
	city.name = "City"
	world.add_child(city)
	city.init_city()
	Fx.init_fx(world)
	GameAudio.create(self)
	Cam.create(world)
	var palace: Dictionary = {}
	for p in city.points:
		if "Ujjayanta" in p["name"]:
			palace = p
			break
	orbit_centre = palace.get("p", Vector3.ZERO)
	step("Building the streets...")
	await get_tree().process_frame
	city.stream_now(orbit_centre)
	var spawn: Dictionary = city.point("spawn")
	var sp: Vector3 = spawn.get("p", Vector3.ZERO)
	city.stream_now(sp)
	step("People of Agartala are waking up...")
	await get_tree().process_frame
	var tr := Traffic.new()
	tr.name = "Traffic"
	world.add_child(tr)
	tr.init_traffic()
	save = Save.read()
	var pl := Player.create(world, sp + Vector3.UP * 0.1, spawn.get("yaw", 0.0))
	pl.set_active(false)
	spawn_point_vehicles()
	make_markers()
	hud = Hud.create(ui_root)
	menus = Menus.create(ui_root)
	apply_settings()
	env.hour = float(save.get("hour", 9.5))
	loading.queue_free()
	to_menu()
	if G.test_mode:
		var t := preload("res://scripts/autotest.gd").new()
		t.name = "AutoTest"
		add_child(t)


func show_loading() -> void:
	loading = ColorRect.new()
	loading.color = Color(0.04, 0.03, 0.03, 1.0)
	loading.mouse_filter = Control.MOUSE_FILTER_STOP
	ui_root.add_child(loading)
	loading.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	Ui.txt(loading, "DANGA", 200, Color.WHITE, "center", Ui.C, Vector2(0, 120), Vector2(1200, 260), Ui.title)
	load_text = Ui.txt(loading, "", 44, Color.WHITE, "center", Ui.C, Vector2(0, -120), Vector2(1400, 60))
	Ui.txt(loading, "MXYAN GAMES OFFICIAL", 34, Color(1, 1, 1, 0.7), "center", Ui.B, Vector2(0, 40), Vector2(1000, 50))


func step(s: String) -> void:
	if load_text:
		load_text.text = s.to_upper()
	G.note(s)


# ------------------------------------------------------------------ settings
func load_settings() -> void:
	var cf := ConfigFile.new()
	var weak := false
	var gpu := RenderingServer.get_video_adapter_name()
	if OS.get_name() == "Android" and ("Mali-G5" in gpu or "Mali-G3" in gpu or "Mali-T" in gpu or "Adreno (TM) 5" in gpu or "PowerVR" in gpu):
		weak = true
	if weak:
		settings["quality"] = 0
		settings["distance"] = 0
	if cf.load("user://settings.cfg") == OK:
		for k in settings:
			settings[k] = int(cf.get_value("settings", k, settings[k]))


func save_settings() -> void:
	var cf := ConfigFile.new()
	for k in settings:
		cf.set_value("settings", k, settings[k])
	cf.save("user://settings.cfg")


func apply_settings() -> void:
	var s := settings
	var vp := get_viewport()
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
	vp.scaling_3d_scale = [0.7, 0.85, 1.0][clampi(s["quality"], 0, 2)]
	vp.msaa_3d = [Viewport.MSAA_DISABLED, Viewport.MSAA_2X, Viewport.MSAA_4X][clampi(s["quality"], 0, 2)]
	Engine.max_fps = 60 if s["quality"] == 2 else 45
	env.set_quality(s["quality"])
	if city:
		city.render_dist = [300.0, 430.0, 580.0][clampi(s["distance"], 0, 2)]
		city.set_normal_maps(s["quality"] >= 1)
	if G.cam:
		G.cam.cam.far = 900.0 if s["distance"] == 0 else 1600.0
		G.cam.sensitivity = 0.45 + s["sens"] * 0.12
	if G.traffic:
		G.traffic.max_cars = [7, 12, 18][clampi(s["density"], 0, 2)]
		G.traffic.max_peds = [9, 15, 22][clampi(s["density"], 0, 2)]
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(0.001, s["sound"] / 10.0)))
	G.audio.music = s["music"] / 10.0
	if hud:
		hud.show_fps = s["fps"] == 1


# ------------------------------------------------------------------ states
func focus() -> Vector3:
	if state == S.MENU or Player.I == null or not Player.I.active:
		return orbit_centre
	return Player.I.vehicle.global_position if Player.I.vehicle else Player.I.global_position


func to_menu() -> void:
	state = S.MENU
	get_tree().paused = false
	var p := Player.I
	if p:
		if p.vehicle:
			p.exit_vehicle(true)
		p.set_active(false)
	G.cam.menu_orbit = true
	G.cam.orbit_centre = orbit_centre
	hud.visible = false
	G.audio.radio_on(false)
	G.audio.menu(true)
	menus.main_menu()


func play(cont: bool) -> void:
	if not cont:
		save = Save.fresh()
		Save.delete()
	else:
		save = Save.read()
	var p := Player.I
	p.set_active(true)
	p.money = int(save["money"])
	p.owned.clear()
	for w in save["owned"]:
		p.owned[int(w)] = true
	if not cont:
		p.ammo.fill(0)
		p.clip.fill(0)
		p.clip[Combat.REVOLVER] = 6
		p.ammo[Combat.REVOLVER] = 36
	else:
		for i in p.ammo.size():
			p.ammo[i] = int(save["ammo"][i])
			p.clip[i] = int(save["clip"][i])
	p.armor = float(save["armor"])
	var t: Array = save["tint"]
	p.tint = Color(t[0], t[1], t[2])
	p.set_outfit(save["outfit"], p.tint)
	p.revive()
	p.equip(Combat.FIST)
	env.hour = float(save["hour"]) if cont else 9.5
	G.audio.station = int(save["station"])
	Wanted.set_stars(0)
	Wanted.never = false
	god_mode = false
	p.speed_mul = 1.0
	p.gravity = -20.0
	var spawn: Dictionary = city.point("spawn")
	var sp := spawn_point()
	city.stream_now(sp)
	p.teleport(sp, spawn.get("yaw", 0.0))
	menus.close()
	G.audio.menu(false)
	G.cam.menu_orbit = false
	G.cam.yaw = rad_to_deg(p.rotation.y)
	G.cam.pitch = 12.0
	hud.visible = true
	state = S.PLAY
	Hud.toast("Welcome back to Agartala" if cont else "Welcome to Agartala", Color.WHITE, 3.0)


func spawn_point() -> Vector3:
	var spawn: Dictionary = city.point("spawn") if city else {}
	return (spawn["p"] + Vector3.UP * 0.1) if not spawn.is_empty() else Vector3.UP


func pause_game() -> void:
	if state == S.PLAY:
		state = S.PAUSED
		get_tree().paused = true


func resume() -> void:
	if state == S.PAUSED:
		state = S.PLAY
		get_tree().paused = false


func save_game() -> void:
	var p := Player.I
	save["money"] = p.money
	save["owned"] = p.owned.keys()
	save["ammo"] = Array(p.ammo)
	save["clip"] = Array(p.clip)
	save["outfit"] = p.outfit
	save["tint"] = [p.tint.r, p.tint.g, p.tint.b]
	save["hour"] = env.hour
	save["armor"] = p.armor
	save["station"] = G.audio.station
	Save.write(save)


func wasted() -> void:
	if state != S.PLAY:
		return
	state = S.DEAD
	Hud.big("WASTED", G.RED, 3.5)
	respawn("hospital", 0.1, "Hospital bill")


func busted() -> void:
	if state != S.PLAY:
		return
	state = S.DEAD
	if Player.I.vehicle:
		Player.I.exit_vehicle(true)
	if Player.I.rig:
		Player.I.rig.play("cower", 0.1)
	Hud.big("BUSTED", G.BLUE, 3.5)
	respawn("police", 0.1, "Fine")


func respawn(where: String, fee: float, what: String) -> void:
	await get_tree().create_timer(3.5, false).timeout
	var pt: Dictionary = city.point(where)
	var pos := spawn_point()
	if not pt.is_empty():
		pos = pt["p"] + G.fwd(pt["yaw"]) * 4.0
	city.stream_now(pos)
	var p := Player.I
	p.revive()
	p.teleport(pos + Vector3.UP * 0.2, pt.get("yaw", 0.0))
	var cost := mini(5000, int(round(p.money * fee)))
	p.money -= cost
	Wanted.set_stars(0)
	state = S.PLAY
	Hud.toast(what + ": ₹" + G.rupees(cost), Color.WHITE, 3.0)


func on_enter_vehicle(_v: Vehicle) -> void:
	var a: GameAudio = G.audio
	a.radio_on(a.station >= 0)
	if a.station >= 0:
		Hud.radio(GameAudio.STATION_NAMES[a.station % GameAudio.STATION_NAMES.size()])


func on_exit_vehicle(_v: Vehicle) -> void:
	G.audio.radio_on(false)


# ------------------------------------------------------------------ the world's fixed vehicles and markers
func spawn_point_vehicles() -> void:
	for i in city.points.size():
		var p: Dictionary = city.points[i]
		if p["kind"] != "vehicle" and p["kind"] != "boat":
			continue
		if point_vehicles.has(i) and is_instance_valid(point_vehicles[i]):
			continue
		var m: String = "speedboat" if p["kind"] == "boat" else p["model"]
		if m == "" or not models.vehicles.has(m):
			continue
		var pos: Vector3 = p["p"]
		if p["kind"] == "boat":
			var wl: float = city.water_level(pos.x, pos.z)
			pos.y = pos.y if is_nan(wl) else wl - 0.2
		var v := Vehicle.spawn(world, m, pos + Vector3.UP * 0.15, p["yaw"], false, Color.WHITE)
		if v == null:
			continue
		v.owned = p["owned"]
		point_vehicles[i] = v


func make_markers() -> void:
	var sh := load("res://shaders/marker.gdshader")
	for p in city.points:
		var c: Color
		match p["kind"]:
			"gunshop":
				c = Color(1.0, 0.3, 0.2)
			"clothes":
				c = Color(0.8, 0.4, 1.0)
			"house":
				c = Color(0.3, 1.0, 0.4)
			"hospital":
				c = Color(1.0, 1.0, 1.0)
			_:
				continue
		var mi := MeshInstance3D.new()
		var cyl := CylinderMesh.new()
		cyl.top_radius = 1.1
		cyl.bottom_radius = 1.1
		cyl.height = 1.5
		cyl.cap_top = false
		cyl.cap_bottom = false
		mi.mesh = cyl
		var mat := ShaderMaterial.new()
		mat.shader = sh
		mat.set_shader_parameter("color", Color(c.r, c.g, c.b, 0.8))
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		world.add_child(mi)
		mi.global_position = p["p"] + Vector3.UP * 0.75
		markers.append(mi)


func _process(delta: float) -> void:
	if state == S.LOADING:
		return
	if state != S.PAUSED:
		G.now += delta
		G.dt = delta
	city.stream(focus(), 2)
	city.update_lamp_lights(G.cam.cam.global_position, env.night)
	if state == S.MENU:
		env.tick(delta * 0.3 - delta)       # the menu runs the clock slower (env adds delta itself)
	if Input.is_action_just_pressed("ui_cancel"):
		if menus.is_open() and state != S.MENU:
			menus.close()
		elif state == S.PLAY:
			menus.pause()
	if state != S.PLAY:
		if hud:
			hud.set_context("", Callable())
		return
	Wanted.tick()
	var p := Player.I
	if p.keep_inside(city.half - 14.0) and G.now > edge_toast:
		edge_toast = G.now + 4.0
		Hud.toast("END OF THE MAP", G.YELLOW, 2.0)
	# shops, house and hospital
	var label := ""
	var act := Callable()
	if p.vehicle == null and not p.dead:
		for pt in city.points:
			if pt["p"].distance_squared_to(p.global_position) > 2.4 * 2.4:
				continue
			match pt["kind"]:
				"gunshop":
					label = "GUN SHOP"
					act = menus.gun_shop
				"clothes":
					label = "CLOTHES"
					act = func(): menus.clothes(false)
				"house":
					label = "HOUSE"
					act = menus.house
				"hospital":
					label = "HEAL ₹500"
					act = heal
	hud.set_context(label, act)
	if G.now > next_point_check:
		next_point_check = G.now + 5.0
		respawn_point_vehicles(p.global_position)


func heal() -> void:
	var p := Player.I
	if p.health >= p.max_health:
		Hud.toast("You are healthy")
		return
	if p.money < 500:
		Hud.toast("Not enough money", G.RED)
		return
	p.money -= 500
	p.health = p.max_health
	G.audio.ui("cash", 0.6)
	Hud.toast("Healed", G.GREEN)


func respawn_point_vehicles(pp: Vector3) -> void:
	for i in point_vehicles.keys():
		var pt: Dictionary = city.points[i]
		var v = point_vehicles[i]
		var gone: bool = not is_instance_valid(v) or v.wrecked or v.global_position.distance_squared_to(pt["p"]) > 40.0 * 40.0
		if not gone or pt["p"].distance_squared_to(pp) < 160.0 * 160.0:
			continue
		if is_instance_valid(v) and v.driver and v.driver.is_player:
			continue
		point_vehicles.erase(i)
	spawn_point_vehicles()


# ------------------------------------------------------------------ cheats
func cheat(code: String) -> String:
	var p := Player.I
	var msg := ""
	match code:
		"1999":
			p.health = p.max_health
			p.armor = 100.0
			msg = "HEALTH & ARMOUR FULL"
		"4545":
			p.add_money(100000)
			msg = "₹1,00,000 ADDED"
		"1122":
			for d in Combat.DEFS:
				p.owned[d["id"]] = true
				if not d["melee"]:
					p.clip[d["id"]] = d["mag"]
					p.ammo[d["id"]] += d["ammo_pack"] * 3
			msg = "ALL WEAPONS"
		"0000":
			Wanted.set_stars(0)
			msg = "WANTED LEVEL CLEARED"
		"7777":
			Wanted.set_stars(5)
			msg = "FIVE STARS!"
		"4321":
			Wanted.never = not Wanted.never
			if Wanted.never:
				Wanted.set_stars(0)
			msg = "NEVER WANTED " + ("ON" if Wanted.never else "OFF")
		"1100":
			god_mode = not god_mode
			msg = "GOD MODE " + ("ON" if god_mode else "OFF")
		"1001":
			p.speed_mul = 1.0 if p.speed_mul > 1.0 else 2.2
			msg = "SUPER RUN " + ("ON" if p.speed_mul > 1.0 else "OFF")
		"1234":
			p.gravity = -4.5 if p.gravity < -10.0 else -20.0
			msg = "MOON GRAVITY " + ("ON" if p.gravity > -10.0 else "OFF")
		"8080":
			msg = spawn_near("sports_car")
		"2323":
			msg = spawn_near("motorbike")
		"6060":
			msg = spawn_near("auto_rickshaw")
		"1515":
			msg = spawn_near("bus")
		"3030":
			msg = spawn_near("police_jeep")
		"9090":
			msg = spawn_near("helicopter")
		"5050":
			msg = spawn_boat()
		"6000":
			env.hour = fposmod(env.hour + 6.0, 24.0)
			msg = "TIME " + env.clock()
		"2222":
			for v in Vehicle.all.duplicate():
				if v != p.vehicle and v.global_position.distance_squared_to(p.global_position) < 60.0 * 60.0:
					v.damage(99999.0, null)
					v.burning = 4.6
			msg = "BOOM!"
		"3131":
			p.teleport(spawn_point(), 0.0)
			city.stream_now(spawn_point())
			msg = "WELCOME HOME"
	if msg != "":
		G.audio.ui("cash", 0.4)
		Hud.toast("CHEAT: " + msg, G.YELLOW, 3.0)
	return msg


func spawn_near(m: String) -> String:
	var p := Player.I
	var at: Vector3 = p.global_position + p.facing() * (9.0 if m == "bus" else (12.0 if m == "helicopter" else 5.0))
	if p.vehicle:
		at = p.vehicle.global_position + p.vehicle.global_transform.basis.x * 6.0
	var yaw := rad_to_deg(p.rotation.y) - 90.0
	if m != "helicopter" and p.vehicle == null:
		var road := nearest_road(p.global_position, 45.0)
		if not road.is_empty():
			at = road[0]            # on the street next to you, pointing along it (not inside a yard or on a roof)
			yaw = road[1]
	at.y = ground_near(at, maxf(at.y, p.global_position.y)) + 0.4
	var v := Vehicle.spawn(world, m, at, yaw, false, Color.WHITE)
	if v == null:
		return ""
	v.parked = false
	return m.replace("_", " ").to_upper() + " READY"


## [point, yaw] of the closest traffic lane (not inside a junction) within reach.
func nearest_road(from: Vector3, reach: float) -> Array:
	if G.traffic == null:
		return []
	var best := reach
	var best_l: Lane = null
	var best_s := 0.0
	for L in G.traffic.lanes:
		if L.junction or L.len < 12.0:
			continue
		var n: Array = L.nearest(from)
		if n[1] < best:
			best = n[1]
			best_l = L
			best_s = n[0]
	if best_l == null:
		return []
	best_s = clampf(best_s, 4.0, best_l.len - 4.0)
	var a := best_l.at(best_s)
	for k in 6:
		var busy := false
		for v in Vehicle.all:
			if v.global_position.distance_squared_to(a[0]) < 25.0:
				busy = true
				break
		if not busy:
			break
		best_s = minf(best_l.len - 2.0, best_s + 6.0)
		a = best_l.at(best_s)
	return [a[0], G.yaw_of(a[1])]


func ground_near(at: Vector3, from_y: float) -> float:
	var q := PhysicsRayQueryParameters3D.create(Vector3(at.x, from_y + 2.5, at.z), Vector3(at.x, from_y - 9.5, at.z), G.L_WORLD)
	var hit := world.get_world_3d().direct_space_state.intersect_ray(q)
	return hit["position"].y if hit else from_y


func spawn_boat() -> String:
	var p := Player.I
	var best: Dictionary = {}
	var bd := 1e12
	for pt in city.points:
		if pt["kind"] == "boat" and pt["p"].distance_squared_to(p.global_position) < bd:
			bd = pt["p"].distance_squared_to(p.global_position)
			best = pt
	var ahead := p.global_position + p.facing() * 8.0
	var wl: float = city.water_level(ahead.x, ahead.z)
	if not is_nan(wl):
		var v := Vehicle.spawn(world, "speedboat", Vector3(ahead.x, wl, ahead.z), rad_to_deg(p.rotation.y), false, Color.WHITE)
		if v:
			v.parked = false
		return "SPEEDBOAT READY"
	if best.is_empty():
		return ""
	var bw: float = city.water_level(best["p"].x, best["p"].z)
	var b := Vehicle.spawn(world, "speedboat", Vector3(best["p"].x, best["p"].y if is_nan(bw) else bw, best["p"].z), best["yaw"], false, Color.WHITE)
	if b:
		b.parked = false
	var side: Vector3 = Basis(Vector3.UP, deg_to_rad(best["yaw"])) * Vector3(3, 1.5, 0)
	p.teleport(best["p"] + side, best["yaw"])
	city.stream_now(best["p"])
	return "BOAT AT " + best["name"].to_upper()


## For the play test.
func test_teleport(p: Vector3, yaw: float) -> void:
	city.stream_now(p)
	Player.I.teleport(p, yaw)
