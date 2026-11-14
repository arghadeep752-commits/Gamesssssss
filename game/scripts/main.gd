extends Node
## RAGINI - The Indian Horror Game.  MXYAN GAMES OFFICIAL.
## Menu -> mode -> intro cutscene -> three days to escape the school -> caught / game over / escape cutscenes.

enum { S_MENU, S_PLAY, S_CUT, S_PAUSE }

const FONT_DIR := "res://assets/downloaded/fonts/"
const MODES := ["EASY", "NORMAL", "HARD"]

var state := S_MENU
var mode := 1
var day := 1
var sensitivity := 1.0
var held := ""
var hide_ref = null
var skip := false
var busy := false
var amb_t := 18.0

var world: Node3D
var level: Level
var player: Player
var ragini: Ragini
var audio: GameAudio
var cut_cam: Camera3D
var env: WorldEnvironment

var ui: CanvasLayer
var hud: Hud
var menu: Control
var fade: ColorRect
var flash: ColorRect
var caption: Label
var big: Label
var sub: Label
var f_title: Font
var f_ui: Font
var f_type: Font
var shots_dir := ""
var test_mode := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shots="):
			shots_dir = a.substr(8)
		if a == "--playtest":
			test_mode = true
	f_title = _font("Creepster-Regular.ttf")
	f_ui = _font("Oswald.ttf")
	f_type = _font("SpecialElite-Regular.ttf")
	var cfg := ConfigFile.new()
	if cfg.load("user://settings.cfg") == OK:
		sensitivity = float(cfg.get_value("game", "sensitivity", 1.0))
	audio = GameAudio.new()
	add_child(audio)
	ui = CanvasLayer.new()
	add_child(ui)
	hud = Hud.new()
	hud.font = f_ui
	hud.visible = false
	ui.add_child(hud)
	hud.interact.connect(_interact)
	hud.drop.connect(_drop)
	hud.crouch.connect(_crouch)
	hud.pause.connect(_pause)
	flash = _rect(Color(0.6, 0, 0, 0))
	fade = _rect(Color(0, 0, 0, 0))
	caption = _label(f_type, 30, Color(0.92, 0.9, 0.85))
	caption.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	caption.offset_top = -150
	caption.offset_bottom = -60
	big = _label(f_title, 110, Color(0.75, 0.04, 0.03))
	big.set_anchors_preset(Control.PRESET_FULL_RECT)
	sub = _label(f_ui, 30, Color(0.85, 0.85, 0.85))
	sub.set_anchors_preset(Control.PRESET_FULL_RECT)
	sub.offset_top = 190
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.mouse_filter = Control.MOUSE_FILTER_IGNORE        # the empty menu layer must never swallow game touches
	ui.add_child(menu)
	_show_main_menu()
	if shots_dir != "":
		_run_shots()
	elif test_mode:
		_run_test()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		match state:
			S_PLAY:
				_pause()
			S_PAUSE:
				_resume()
			S_MENU:
				if menu.get_child_count() > 0 and not busy:
					_show_main_menu()


func _font(n: String) -> Font:
	if ResourceLoader.exists(FONT_DIR + n):
		return load(FONT_DIR + n)
	return ThemeDB.fallback_font


func _rect(c: Color) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(r)
	return r


func _label(f: Font, size: int, c: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", f)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", c)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(l)
	return l


# ============================================================================================== menus
func _clear_menu() -> void:
	for c in menu.get_children():
		c.queue_free()


func _menu_bg() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 1)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	menu.add_child(bg)


func _text(parent: Control, t: String, f: Font, size: int, c: Color, y: float) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_font_override("font", f)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", c)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.set_anchors_preset(Control.PRESET_TOP_WIDE)
	l.anchor_top = y
	l.anchor_bottom = y
	l.offset_top = 0
	l.offset_bottom = size * 1.4
	parent.add_child(l)
	return l


func _button(parent: Control, t: String, y: float, cb: Callable, size := 46) -> Button:
	var b := Button.new()
	b.text = t
	b.flat = true
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", f_ui)
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", Color(0.92, 0.92, 0.92))
	b.add_theme_color_override("font_pressed_color", Color(0.8, 0.1, 0.08))
	b.add_theme_color_override("font_hover_color", Color(1, 1, 1))
	b.anchor_left = 0.5
	b.anchor_right = 0.5
	b.anchor_top = y
	b.anchor_bottom = y
	b.offset_left = -220
	b.offset_right = 220
	b.offset_top = 0
	b.offset_bottom = size * 1.7
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


func _slider(parent: Control, y: float) -> void:
	_text(parent, "SENSITIVITY", f_ui, 34, Color(0.85, 0.85, 0.85), y)
	var s := HSlider.new()
	s.min_value = 0.3
	s.max_value = 2.5
	s.step = 0.05
	s.value = sensitivity
	s.anchor_left = 0.5
	s.anchor_right = 0.5
	s.anchor_top = y + 0.1
	s.anchor_bottom = y + 0.1
	s.offset_left = -260
	s.offset_right = 260
	s.offset_bottom = 60
	s.scale = Vector2(1, 1)
	s.custom_minimum_size = Vector2(520, 60)
	var grab := _dot(22)
	s.add_theme_icon_override("grabber", grab)
	s.add_theme_icon_override("grabber_highlight", grab)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.35, 0.35, 0.35)
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	s.add_theme_stylebox_override("slider", sb)
	var sa := StyleBoxFlat.new()
	sa.bg_color = Color(0.8, 0.1, 0.08)
	sa.content_margin_top = 4
	sa.content_margin_bottom = 4
	s.add_theme_stylebox_override("grabber_area", sa)
	s.add_theme_stylebox_override("grabber_area_highlight", sa)
	s.value_changed.connect(func(v):
		sensitivity = v
		if player:
			player.sensitivity = v
		var cfg := ConfigFile.new()
		cfg.set_value("game", "sensitivity", v)
		cfg.save("user://settings.cfg"))
	parent.add_child(s)


func _dot(r: int) -> ImageTexture:
	var img := Image.create(r * 2, r * 2, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for x in r * 2:
		for y in r * 2:
			if Vector2(x - r + 0.5, y - r + 0.5).length() < r - 1:
				img.set_pixel(x, y, Color(1, 1, 1, 1))
	return ImageTexture.create_from_image(img)


func _show_main_menu() -> void:
	state = S_MENU
	get_tree().paused = false
	hud.visible = false
	big.text = ""
	sub.text = ""
	caption.text = ""
	fade.color.a = 0.0
	_clear_menu()
	_menu_bg()
	_text(menu, "RAGINI", f_title, 150, Color(0.72, 0.03, 0.03), 0.09)
	_text(menu, "THE INDIAN HORROR GAME", f_ui, 30, Color(0.8, 0.8, 0.8), 0.37)
	_button(menu, "PLAY", 0.5, _show_modes)
	_button(menu, "SETTINGS", 0.64, _show_settings)
	_text(menu, "MXYAN GAMES OFFICIAL", f_ui, 24, Color(0.6, 0.6, 0.6), 0.9)
	audio.stop_all()
	audio.loop("menu_music", -8.0)


func _show_settings() -> void:
	_clear_menu()
	_menu_bg()
	_text(menu, "SETTINGS", f_ui, 54, Color(0.92, 0.92, 0.92), 0.12)
	_slider(menu, 0.36)
	_button(menu, "BACK", 0.72, _show_main_menu)


func _show_modes() -> void:
	_clear_menu()
	_menu_bg()
	_text(menu, "SELECT MODE", f_ui, 54, Color(0.92, 0.92, 0.92), 0.1)
	for i in 3:
		_button(menu, MODES[i], 0.3 + i * 0.14, _start_game.bind(i))
	_button(menu, "BACK", 0.78, _show_main_menu, 34)


func _pause() -> void:
	if state != S_PLAY:
		return
	state = S_PAUSE
	get_tree().paused = true
	hud.visible = false
	_clear_menu()
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.8)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	menu.add_child(dim)
	_button(menu, "RESUME", 0.16, _resume)
	_slider(menu, 0.36)
	_button(menu, "MAIN MENU", 0.7, _quit_to_menu)


func _resume() -> void:
	_clear_menu()
	get_tree().paused = false
	hud.reset_touches()
	hud.visible = true
	state = S_PLAY


func _quit_to_menu() -> void:
	get_tree().paused = false
	_free_world()
	_show_main_menu()


# ============================================================================================== world
func _free_world() -> void:
	if world:
		world.queue_free()
	world = null
	level = null
	player = null
	ragini = null
	cut_cam = null
	held = ""
	hide_ref = null


func _build_world() -> bool:
	_free_world()
	world = Node3D.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	env = WorldEnvironment.new()
	var e := Environment.new()
	var hdr := "res://assets/downloaded/sky/night.hdr"
	if ResourceLoader.exists(hdr):
		var sky := Sky.new()
		var pm := PanoramaSkyMaterial.new()
		pm.panorama = load(hdr)
		pm.energy_multiplier = 0.5
		sky.sky_material = pm
		e.sky = sky
		e.background_mode = Environment.BG_SKY
	else:
		e.background_mode = Environment.BG_COLOR
		e.background_color = Color(0.012, 0.016, 0.03)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.5, 0.55, 0.7)
	e.ambient_light_energy = 0.32
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.fog_enabled = true
	e.fog_light_color = Color(0.02, 0.025, 0.04)
	e.fog_density = 0.018
	env.environment = e
	world.add_child(env)
	level = Level.new()
	level.audio = audio
	world.add_child(level)
	if not level.build():
		return false
	player = Player.new()
	player.hud = hud
	player.audio = audio
	player.sensitivity = sensitivity
	world.add_child(player)
	ragini = Ragini.new()
	ragini.level = level
	ragini.player = player
	ragini.audio = audio
	ragini.setup(mode)
	world.add_child(ragini)
	ragini.build()
	ragini.caught.connect(_on_caught)
	level.noise.connect(ragini.hear)
	cut_cam = Camera3D.new()
	cut_cam.fov = 55
	cut_cam.far = 150
	world.add_child(cut_cam)
	return true


func _place_start() -> void:
	var sp = level.meta["spawn"]["pos"]
	player.global_position = Vector3(sp[0], 0.05, sp[2])
	player.face(player.global_position + Vector3(-5, 0, 0))
	player.set_crouch(false)
	player.hidden = false
	player.frozen = false
	var pts: Array = level.meta["patrol"]
	var far = pts[0]
	var best := 0.0
	for p in pts:
		var d := Vector3(p[0], 0, p[2]).distance_to(player.global_position)
		if d > best:
			best = d
			far = p
	ragini.global_position = Vector3(far[0], 0, far[2])
	ragini.freeze(false)
	ragini._pick_patrol()


func _start_game(m: int) -> void:
	if busy:
		return
	busy = true
	mode = m
	day = 1
	_clear_menu()
	_menu_bg()
	_text(menu, "LOADING...", f_ui, 40, Color(0.8, 0.8, 0.8), 0.45)
	await get_tree().process_frame
	await get_tree().process_frame
	var ok := _build_world()
	busy = false
	if not ok:
		_clear_menu()
		_menu_bg()
		_text(menu, "GAME FILES MISSING", f_ui, 40, Color(0.8, 0.2, 0.2), 0.4)
		_button(menu, "BACK", 0.6, _show_main_menu)
		return
	audio.stop_all()
	audio.loop("night", -13.0)
	audio.loop("wind", -24.0)
	audio.loop("music_raga", -9.0)        # the intro cutscene plays over a real raga recording
	_place_start()
	await _intro()
	audio.stop("music_raga")
	audio.loop("drone", -15.0)            # tanpura drone under the night ambience while playing
	_begin_day()


func _begin_day() -> void:
	_clear_menu()
	state = S_PLAY
	player.cam.current = true
	player.frozen = false
	hud.day_text = "DAY %d" % day
	hud.reset_touches()
	hud.visible = true
	hud.refresh()
	big.text = ""
	sub.text = ""
	caption.text = ""


# ============================================================================================== play
func _process(dt: float) -> void:
	if flash.color.a > 0.0:
		flash.color.a = maxf(0.0, flash.color.a - dt * 1.5)
	if state != S_PLAY or player == null:
		return
	var lab := ""
	var can := false
	if player.hidden:
		lab = "Leave"
		can = true
	else:
		var t := level.target(player.head(), player.forward(), held)
		if not t.is_empty():
			lab = t["label"]
			can = true
	if lab != hud.label_text or can != hud.can_interact or hud.holding != (held != "") or hud.crouched != player.crouched:
		hud.label_text = lab
		hud.can_interact = can
		hud.holding = held != ""
		hud.crouched = player.crouched
		hud.refresh()
	hud.queue_redraw()
	if hide_ref != null:
		hide_ref["t"] = move_toward(hide_ref["t"], hide_ref["target"], dt * 3.0)
		level.set_hide_doors(hide_ref, hide_ref["t"])
	if audio:
		audio.loop("heartbeat", -4.0 if ragini.state == Ragini.CHASE else -60.0)
		amb_t -= dt
		if amb_t <= 0.0:
			amb_t = randf_range(22.0, 45.0)
			var pick: String = ["dog_howl", "owl", "dog_howl", "laugh"][randi() % 4]
			var off := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized() * randf_range(12.0, 22.0)
			audio.play3d(pick, player.global_position + off + Vector3(0, 3, 0), -10.0 if pick != "laugh" else -14.0)


func _crouch() -> void:
	if state == S_PLAY and not player.hidden:
		player.set_crouch(not player.crouched)


func _interact() -> void:
	if state != S_PLAY:
		return
	if player.hidden:
		_leave_hide()
		return
	var t := level.target(player.head(), player.forward(), held)
	if t.is_empty():
		return
	match t["kind"]:
		"item":
			_pick(t["ref"])
		"door":
			var d: Dictionary = t["ref"]
			if d["lock"] != null and d["lock"] != "":
				if held == d["lock"]:
					d["lock"] = null
					audio.play3d("unlock", d["pos"], 0.0)
					hud.show_message("Unlocked")
					_consume_held()
				else:
					audio.play3d("door_locked", d["pos"], -2.0)
					hud.show_message("Locked. Needs the %s" % String(level.meta["items"][d["lock"]]["label"]).capitalize())
			else:
				level.toggle_door(d)
		"hide":
			_enter_hide(t["ref"])
		"plank":
			if held == "hammer":
				_hit_plank(t["ref"])
			else:
				hud.show_message("Nailed shut. Needs the Hammer")
		"maindoor":
			hud.show_message("Planks are nailed across the door")
		"padlock":
			if held == "main_key":
				_escape()
			else:
				audio.play3d("door_locked", level.doors["door_main"]["pos"], -2.0)
				hud.show_message("Locked. Needs the Main Door Key")


func _pick(it: Dictionary) -> void:
	if held != "":
		_drop(true)
	var n: Node3D = it["node"]
	n.get_parent().remove_child(n)
	player.cam.get_node("Hold").add_child(n)
	n.position = Vector3.ZERO
	n.rotation = Vector3(deg_to_rad(-20), deg_to_rad(110), deg_to_rad(15))
	if it["id"] != "hammer":
		n.scale = Vector3(1.6, 1.6, 1.6)
	it["held"] = true
	held = it["id"]
	level._relight(n, 0.55)
	audio.play("pickup", -6.0)


func _drop(quiet := false) -> void:
	if held == "" or player == null:
		return
	var it: Dictionary = level.items[held]
	var n: Node3D = it["node"]
	n.get_parent().remove_child(n)
	level.model.add_child(n)
	var f := player.forward()
	f.y = 0
	f = f.normalized() if f.length() > 0.01 else Vector3(0, 0, -1)
	var p := player.global_position + f * 0.7
	var q := PhysicsRayQueryParameters3D.create(player.head(), Vector3(p.x, player.head().y, p.z), 1)
	if not player.get_world_3d().direct_space_state.intersect_ray(q).is_empty():
		p = player.global_position
	n.global_position = Vector3(p.x, 0.03, p.z)
	n.rotation = Vector3(0, randf() * TAU, 0)
	n.scale = Vector3.ONE
	it["held"] = false
	held = ""
	level._relight(n)
	if not quiet:
		audio.play3d("drop", n.global_position, 0.0)
		level.noise.emit(n.global_position, 9.0)


func _consume_held() -> void:
	if held == "":
		return
	var it: Dictionary = level.items[held]
	it["node"].visible = false
	it["held"] = true
	held = ""


func _hit_plank(p: Dictionary) -> void:
	p["hits"] += 1
	audio.play3d("hammer_hit", p["pos"], 3.0)
	level.noise.emit(p["pos"], 16.0)
	if p["hits"] >= 2:
		p["gone"] = true
		level.planks_left -= 1
		var n: Node3D = p["node"]
		audio.play3d("nail_creak", p["pos"], 0.0)
		var tw := create_tween()
		tw.tween_property(n, "position", Vector3(n.position.x + randf_range(-0.2, 0.2), 0.03, n.position.z + 0.45), 0.45).set_ease(Tween.EASE_IN)
		tw.parallel().tween_property(n, "rotation", Vector3(deg_to_rad(88), randf_range(-0.4, 0.4), 0), 0.45)
		tw.tween_callback(func(): audio.play3d("plank_fall", p["pos"], 2.0))
		if level.planks_left == 0:
			hud.show_message("The planks are off")


func _enter_hide(h: Dictionary) -> void:
	hide_ref = h
	h["target"] = 0.22
	player.set_crouch(false)
	player.hidden = true
	player.global_position = h["pos"] + Vector3(0, 0.12, 0)
	var f: Vector3 = h["front"]
	player.yaw = atan2(-f.x, -f.z)
	player.pitch = 0.0
	audio.play3d("door_close", h["pos"], -8.0)


func _leave_hide() -> void:
	if hide_ref == null:
		player.hidden = false
		return
	var h: Dictionary = hide_ref
	player.global_position = h["pos"] + h["front"] * 0.95 + Vector3(0, 0.05, 0)
	player.hidden = false
	h["target"] = 0.0
	audio.play3d("door_open", h["pos"], -8.0)
	level.noise.emit(h["pos"], 5.0)


# ============================================================================================== cutscenes
func _input(e: InputEvent) -> void:
	if state == S_CUT and e is InputEventScreenTouch and e.pressed:
		skip = true


func _wait(t: float) -> void:
	var left := t
	while left > 0.0 and not skip:
		await get_tree().process_frame
		left -= get_process_delta_time()


func _fade_to(a: float, t: float) -> void:
	var from := fade.color.a
	var k := 0.0
	while k < 1.0:
		await get_tree().process_frame
		k += get_process_delta_time() / maxf(t, 0.01) * (4.0 if skip else 1.0)
		fade.color.a = lerpf(from, a, clampf(k, 0, 1))


func _shot(from: Vector3, to: Vector3, look_a: Vector3, look_b: Vector3, dur: float, text: String) -> void:
	cut_cam.current = true
	cut_cam.global_position = from
	cut_cam.look_at(look_a)
	caption.text = text
	await _fade_to(0.0, 0.7)
	var k := 0.0
	while k < 1.0 and not skip:
		await get_tree().process_frame
		k += get_process_delta_time() / dur
		var e := smoothstep(0.0, 1.0, clampf(k, 0, 1))
		cut_cam.global_position = from.lerp(to, e)
		cut_cam.look_at(look_a.lerp(look_b, e))
	await _fade_to(1.0, 0.6)
	caption.text = ""


func _intro() -> void:
	state = S_CUT
	skip = false
	_clear_menu()
	hud.visible = false
	fade.color.a = 1.0
	ragini.freeze(true)
	player.frozen = true
	var o: Dictionary = level.meta["outside"]
	var gate := level.v3(o["gate"])
	var door := level.v3(o["door"])
	await _shot(gate + Vector3(1.5, 1.5, 2.5), gate + Vector3(0.3, 1.6, -3.5), door + Vector3(0, 2.4, 0), door + Vector3(0, 2.6, 0), 6.0,
		"Adarsh Vidyalaya. Locked and forgotten since 1998.")
	if not skip:
		await _shot(Vector3(-7.8, 1.5, -2.2), Vector3(-2.0, 1.5, -2.2), Vector3(8, 1.4, -2.2), Vector3(8, 1.4, -2.6), 6.0,
			"They say Ragini ma'am never left her school.")
	if not skip:
		var c5 := Vector3(-13.0, 0, 2.5)
		ragini.global_position = c5
		ragini.rotation.y = atan2(-1.0, 0.0)
		ragini.play("idle")
		await _shot(Vector3(-8.0, 1.3, 4.6), Vector3(-9.6, 1.4, 3.4), c5 + Vector3(0, 1.4, 0), c5 + Vector3(0, 1.55, 0), 6.0,
			"Children who stayed back after the last bell were never seen again.")
	if not skip:
		caption.text = ""
		big.text = ""
		sub.offset_top = 0
		sub.text = "Tonight, you stayed back."
		await _wait(2.6)
	sub.text = ""
	sub.offset_top = 190
	skip = false
	_place_start()
	player.cam.current = true
	big.text = "DAY 1"
	sub.text = "Find a way out of the school."
	audio.play("bell", -6.0)
	await _wait(2.2)
	big.text = ""
	sub.text = ""
	skip = false
	await _fade_to(0.0, 1.2)


func _on_caught() -> void:
	if state != S_PLAY:
		return
	state = S_CUT
	skip = false
	hud.visible = false
	hud.reset_touches()
	player.frozen = true
	if player.hidden:
		_leave_hide()
		player.global_position = ragini.global_position + ragini.face_dir() * 1.0
	hide_ref = null
	var to := ragini.eyes() - player.head()
	player.yaw = atan2(-to.x, -to.z)
	player.pitch = atan2(to.y, Vector2(to.x, to.z).length())
	audio.play("scream", 0.0)
	await get_tree().create_timer(0.55).timeout
	audio.play("whack", 4.0)
	flash.color.a = 0.85
	await get_tree().create_timer(0.3).timeout
	audio.play("whack", 4.0, 0.9)
	flash.color.a = 0.85
	await _fade_to(1.0, 0.5)
	audio.set_vol("heartbeat", -60.0)
	if held != "":
		_drop(true)
	day += 1
	if day > 3:
		await _game_over()
		return
	_place_start()
	big.text = "DAY %d" % day
	sub.text = "She let you live. This time." if day == 2 else "This is your last day."
	await get_tree().create_timer(2.6).timeout
	big.text = ""
	sub.text = ""
	await _fade_to(0.0, 1.0)
	_begin_day()


func _game_over() -> void:
	ragini.freeze(true)
	var p := Vector3(0, 0, -8.0)
	ragini.global_position = p
	ragini.rotation.y = 0.0
	cut_cam.current = true
	cut_cam.global_position = p + Vector3(0.25, 1.5, -2.2)
	cut_cam.look_at(p + Vector3(0, 1.5, 0))
	ragini.rotation.y = atan2(-(cut_cam.global_position.x - p.x), -(cut_cam.global_position.z - p.z))
	ragini.play("scream", 0.1)
	audio.play("scream", 2.0, 0.85)
	await _fade_to(0.0, 0.3)
	var k := 0.0
	while k < 1.5:
		await get_tree().process_frame
		k += get_process_delta_time()
		cut_cam.global_position = cut_cam.global_position.lerp(p + Vector3(0.05, 1.56, -0.75), get_process_delta_time() * 1.6)
		cut_cam.look_at(p + Vector3(0, 1.58, 0))
	await _fade_to(1.0, 0.25)
	big.text = "GAME OVER"
	sub.text = "No one leaves Ragini ma'am's school."
	await get_tree().create_timer(3.5).timeout
	_free_world()
	_show_main_menu()


func _escape() -> void:
	state = S_CUT
	skip = false
	hud.visible = false
	player.frozen = true
	ragini.freeze(true)
	for n in level.padlock_nodes:
		n.visible = false
	audio.play("unlock", 2.0)
	_consume_held()
	await get_tree().create_timer(0.7).timeout
	level.open_main()
	await get_tree().create_timer(1.3).timeout
	await _fade_to(1.0, 0.6)
	var o: Dictionary = level.meta["outside"]
	var gate := level.v3(o["gate"])
	var door := level.v3(o["door"])
	audio.set_vol("heartbeat", -60.0)
	await _shot(door + Vector3(0, 1.6, 1.2), gate + Vector3(0, 1.6, -1.5), gate + Vector3(0, 1.5, 6), gate + Vector3(0, 1.5, 6), 5.0,
		"The night air. The gate. You ran.")
	ragini.global_position = door + Vector3(0, 0, -0.6)
	ragini.rotation.y = PI
	ragini.play("scream", 0.1)
	audio.play("scream", 0.0, 0.9)
	await _shot(gate + Vector3(0.4, 1.6, 0.5), gate + Vector3(0.4, 1.6, 2.5), door + Vector3(0, 1.5, 0), door + Vector3(0, 1.5, 0), 4.0,
		"She cannot follow you past the door.")
	big.text = "YOU ESCAPED"
	sub.text = "MXYAN GAMES OFFICIAL"
	await get_tree().create_timer(4.5).timeout
	_free_world()
	_show_main_menu()


# ============================================================================================== build check (not used in play)
func _snap(n: String) -> void:
	await RenderingServer.frame_post_draw
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(shots_dir.path_join(n + ".png"))
	print("RAGINI shot ", n)


func _run_shots() -> void:
	DirAccess.make_dir_recursive_absolute(shots_dir)
	await get_tree().create_timer(0.5).timeout
	await _snap("01_menu")
	_show_settings()
	await _snap("02_settings")
	_show_modes()
	await _snap("03_modes")
	mode = 1
	_clear_menu()
	if not _build_world():
		print("RAGINI shots: world failed")
		get_tree().quit(1)
		return
	_place_start()
	ragini.freeze(true)
	_begin_day()
	fade.color.a = 0.0
	var views := [["04_spawn", Vector3(-10.5, 0, 2.6), Vector3(-14, 1.3, 2.6)], ["05_class_back", Vector3(-13.2, 0, 0.6), Vector3(-8, 1.0, 4.5)],
		["06_main_door", Vector3(0, 0, 1.6), Vector3(0, 1.3, 6)], ["07_veranda", Vector3(-7.8, 0, -2.2), Vector3(8, 1.3, -2.2)],
		["08_courtyard", Vector3(6.2, 0, -13.6), Vector3(-3, 1.6, -7)], ["09_principal", Vector3(-3.1, 0, 0.4), Vector3(-5.4, 0.9, 4.6)],
		["10_store", Vector3(9.7, 0, -9.7), Vector3(13.2, 0.5, -9.3)], ["11_hall", Vector3(2, 0, -16), Vector3(-6, 1.4, -21)],
		["12_library", Vector3(-9.6, 0, -11.5), Vector3(-14, 1.3, -11.5)], ["13_kitchen", Vector3(6.2, 0, -16), Vector3(12.5, 1.0, -21)],
		["14_staff", Vector3(3.1, 0, 0.4), Vector3(5.5, 0.9, 4)], ["15_toilet", Vector3(9.8, 0, -13.2), Vector3(13, 1.2, -13.5)]]
	for v in views:
		player.global_position = v[1] + Vector3(0, 0.05, 0)
		player.face(v[2])
		player.pitch = atan2(v[2].y - 1.6, Vector2(v[2].x - v[1].x, v[2].z - v[1].z).length())
		await get_tree().create_timer(0.25).timeout
		await _snap(v[0])
	# Ragini in the veranda
	player.global_position = Vector3(-2.5, 0.05, -2.2)
	player.face(Vector3(3, 0, -2.2))
	player.pitch = 0.0
	ragini.global_position = Vector3(1.0, 0, -2.2)
	ragini.rotation.y = atan2(1.0, 0.0)
	ragini.play("walk")
	await get_tree().create_timer(0.5).timeout
	await _snap("16_ragini")
	ragini.global_position = Vector3(-1.3, 0, -2.2)
	ragini.play("attack", 0.0)
	await get_tree().create_timer(0.45).timeout
	await _snap("17_ragini_close")
	# an item in hand + interact prompt
	var it: Dictionary = level.items["hammer"]
	player.global_position = it["node"].global_position + Vector3(-1.2, 0.05 - it["node"].global_position.y, 0.3)
	player.face(it["node"].global_position)
	player.pitch = atan2(it["node"].global_position.y - 1.6, 1.25)
	await get_tree().create_timer(0.4).timeout
	await _snap("18_item_prompt")
	_interact()
	player.global_position = Vector3(0, 0.05, 3.9)
	player.face(Vector3(0, 0, 6))
	player.pitch = -0.1
	await get_tree().create_timer(0.4).timeout
	await _snap("19_planks_hammer")
	# path-finding sanity: every patrol point is reachable
	var bad := 0
	for p in level.meta["patrol"]:
		if level.find_path(Vector3(0, 0, -8), Vector3(p[0], 0, p[2])).is_empty():
			bad += 1
	print("RAGINI patrol points unreachable: ", bad, " items: ", level.items.size(), " doors: ", level.doors.size(), " hides: ", level.hides.size(),
		" planks: ", level.planks.size(), " anim: ", ragini.anim != null)
	get_tree().quit()


# ============================================================================================== automated play test (build check)
func _touch(i: int, p: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = i
	e.position = p
	e.pressed = pressed
	Input.parse_input_event(e)


func _drag(i: int, p: Vector2, rel: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = i
	e.position = p
	e.relative = rel
	Input.parse_input_event(e)


func _t(msg: String) -> void:
	print("RAGINI_TEST ", msg)


func _run_test() -> void:
	await get_tree().create_timer(0.3).timeout
	_t("menu ok")
	_start_game(1)
	await get_tree().create_timer(0.6).timeout
	skip = true
	while state != S_PLAY:
		skip = true
		await get_tree().process_frame
	_t("day %d started, state play" % day)
	# real touches on the joystick and the look area
	var vs := get_viewport().get_visible_rect().size
	var p0 := player.global_position
	var jc := hud.joy_center()
	_touch(0, jc, true)
	_drag(0, jc + Vector2(0, -80), Vector2(0, -80))
	await get_tree().create_timer(1.2).timeout
	_touch(0, jc + Vector2(0, -80), false)
	_t("joystick moved player %.2f m" % player.global_position.distance_to(p0))
	var y0 := player.yaw
	_touch(1, Vector2(vs.x * 0.7, vs.y * 0.5), true)
	_drag(1, Vector2(vs.x * 0.7 + 120, vs.y * 0.5), Vector2(120, 0))
	await get_tree().create_timer(0.2).timeout
	_touch(1, Vector2(vs.x * 0.7 + 120, vs.y * 0.5), false)
	_t("look drag turned %.2f rad" % absf(player.yaw - y0))
	# crouch button by touch
	_touch(2, hud.r_crouch().get_center(), true)
	_touch(2, hud.r_crouch().get_center(), false)
	await get_tree().process_frame
	_t("crouch button -> crouched=%s" % player.crouched)
	_crouch()
	# items: walk to each, pick it up with the hand button, drop it
	for id in ["office_key", "store_key", "hammer", "main_key"]:
		var it: Dictionary = level.items[id]
		var ip: Vector3 = it["node"].global_position
		player.global_position = Vector3(ip.x, 0.05, ip.z) + Vector3(0.9, 0, 0.9)
		player.face(ip)
		player.pitch = atan2(ip.y - player.eye - 0.05, Vector2(0.9, 0.9).length())
		await get_tree().create_timer(0.15).timeout
		var tg := level.target(player.head(), player.forward(), held)
		_t("%s target=%s can_interact=%s" % [id, tg.get("label", "-"), hud.can_interact])
		if hud.can_interact:
			_touch(3, hud.r_hand().get_center(), true)
			_touch(3, hud.r_hand().get_center(), false)
			await get_tree().process_frame
		_t("  held=%s" % held)
	_touch(4, hud.r_drop().get_center(), true)
	_touch(4, hud.r_drop().get_center(), false)
	await get_tree().process_frame
	_t("drop button -> held='%s'" % held)
	# doors: unlock the office with its key
	var d: Dictionary = level.doors["door_principal"]
	_pick(level.items["office_key"])
	player.global_position = d["pos"] + Vector3(1.0, -1.1, 0.0)
	player.face(d["pos"])
	player.pitch = 0.0
	_t("dbg yaw after face=%.2f" % player.yaw)
	await get_tree().physics_frame
	await get_tree().physics_frame
	_t("dbg yaw after physics=%.2f rot=%.2f" % [player.yaw, player.rotation.y])
	var tgd := level.target(player.head(), player.forward(), held)
	var dd: Vector3 = d["pos"] - player.head()
	_t("dbg head=%s fwd=%s dist=%.2f dot=%.2f lock=%s" % [player.head(), player.forward(), dd.length(), player.forward().dot(dd.normalized()), str(d["lock"])])
	_t("office door target=%s/%s held=%s pos=%s door=%s" % [tgd.get("kind", "-"), tgd.get("label", "-"), held, player.global_position, d["pos"]])
	_interact()
	_t("office door lock after key: %s" % str(d["lock"]))
	_interact()
	await get_tree().create_timer(0.8).timeout
	_t("office door open=%s" % d["open"])
	# hide in an almirah, Ragini comes by, leave again
	var h: Dictionary = level.hides[0]
	_enter_hide(h)
	_t("hidden=%s" % player.hidden)
	_leave_hide()
	_t("left hide, hidden=%s" % player.hidden)
	# Ragini: patrol for a while, then see the player and catch them
	player.global_position = Vector3(-4, 0.05, -2.2)
	ragini.global_position = Vector3(4, 0, -2.2)
	ragini.freeze(false)
	ragini._pick_patrol()
	player.face(ragini.global_position)
	await get_tree().create_timer(1.0).timeout
	ragini.rotation.y = atan2(1.0, 0.0)
	var tw := 0.0
	while state == S_PLAY and tw < 12.0:
		await get_tree().process_frame
		tw += get_process_delta_time()
	_t("ragini state=%d game state=%d after %.1fs" % [ragini.state, state, tw])
	while state != S_PLAY:
		await get_tree().process_frame
	_t("now day %d" % day)
	# planks + lock + escape
	var it2: Dictionary = level.items["hammer"]
	it2["held"] = false
	if it2["node"].get_parent() != level.model:
		it2["node"].get_parent().remove_child(it2["node"])
		level.model.add_child(it2["node"])
	_pick(it2)
	player.global_position = Vector3(0, 0.05, 4.5)
	for p in level.planks:
		player.face(p["pos"])
		player.pitch = atan2(p["pos"].y - player.head().y, (p["pos"] - player.global_position).length())
		await get_tree().process_frame
		for k in 2:
			var tg2 := level.target(player.head(), player.forward(), held)
			if tg2.get("kind", "") == "plank":
				_hit_plank(tg2["ref"])
			else:
				_hit_plank(p)
	await get_tree().create_timer(0.6).timeout
	_t("planks left=%d" % level.planks_left)
	var mk: Dictionary = level.items["main_key"]
	mk["held"] = false
	if mk["node"].get_parent() != level.model:
		mk["node"].get_parent().remove_child(mk["node"])
		level.model.add_child(mk["node"])
	_pick(mk)
	player.face(level.doors["door_main"]["pos"])
	player.pitch = 0.0
	await get_tree().process_frame
	var tg3 := level.target(player.head(), player.forward(), held)
	_t("main door target=%s" % tg3.get("kind", "-"))
	skip = true
	_interact()
	var tt := 0.0
	while state != S_MENU and tt < 30.0:
		skip = true
		await get_tree().process_frame
		tt += get_process_delta_time()
	_t("after escape state=%d (0 = menu)" % state)
	_t("sounds available: footstep=%s payal=%s scream=%s menu_music=%s" % [audio.has("footstep_1"), audio.has("payal"), audio.has("scream"), audio.has("menu_music")])
	_t("done")
	get_tree().quit()
