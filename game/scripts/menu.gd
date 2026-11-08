extends Node3D
## Main menu: a dark corridor with Chaya standing at the far end, red title, START and SETTINGS.

const GhostScript := preload("res://game/scripts/ghost.gd")
const GAME := "res://game/game.tscn"
const RED := Color(0.86, 0.02, 0.02)
const FONT_TITLE := "res://assets/downloaded/fonts/Creepster-Regular.ttf"
const FONT_DEV := "res://assets/downloaded/fonts/NotoSansDevanagari.ttf"

var cam: Camera3D
var ghost: CharacterBody3D
var lamps: Array = []
var _t := 0.0
var _flick := 0.0
var _next_event := 9.0
var _step := 0
var font: Font
var root_ui: Control
var main_box: Control
var settings_box: Control
var fade: ColorRect
var _starting := false
var _sens_label: Label
var _slider: HSlider

func _ready() -> void:
	randomize()
	font = load(FONT_TITLE) if ResourceLoader.exists(FONT_TITLE) else ThemeDB.fallback_font
	_build_scene()
	_build_ui()
	# a drone plus the real night ambience (the drone alone is too deep for phone speakers)
	Sfx.loop_on("menu_music", self, -2.0)
	Sfx.loop_on("ambient", self, -6.0)

func _tiled(mat_name: String, tile: float) -> StandardMaterial3D:
	var m := Mats.get_material(mat_name).duplicate() as StandardMaterial3D
	m.vertex_color_use_as_albedo = false
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_scale = Vector3.ONE / tile
	return m

func _box(pos: Vector3, size: Vector3, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.position = pos
	add_child(mi)

func _build_scene() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.3, 0.25, 0.24)
	env.ambient_light_energy = 0.2
	env.fog_enabled = true
	env.fog_light_color = Color(0.02, 0.015, 0.015)
	env.fog_density = 0.07
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.1
	env.adjustment_saturation = 0.88
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var floor_m := _tiled("floor_wood", 2.2)
	var wall_lo := _tiled("wall_wood", 1.7)
	var wall_hi := _tiled("wall_plaster", 2.4)
	var ceil_m := _tiled("ceiling_wood", 2.0)
	var trim_m := _tiled("trim_wood", 1.0)
	_box(Vector3(0, -0.05, -6), Vector3(2.6, 0.1, 18), floor_m)
	_box(Vector3(0, 3.05, -6), Vector3(2.6, 0.1, 18), ceil_m)
	_box(Vector3(-1.35, 0.5, -6), Vector3(0.1, 1.05, 18), wall_lo)
	_box(Vector3(1.35, 0.5, -6), Vector3(0.1, 1.05, 18), wall_lo)
	_box(Vector3(-1.35, 2.025, -6), Vector3(0.1, 1.95, 18), wall_hi)
	_box(Vector3(1.35, 2.025, -6), Vector3(0.1, 1.95, 18), wall_hi)
	_box(Vector3(0, 1.5, -15), Vector3(2.8, 3.1, 0.1), wall_hi)
	for z in [-1.0, -4.0, -7.0, -10.0, -13.0]:
		_box(Vector3(0, 2.9, z), Vector3(2.6, 0.2, 0.18), trim_m)
	# a door and a doorway frame at the end
	_box(Vector3(0, 1.1, -14.9), Vector3(1.2, 2.2, 0.08), Mats.get_material("door_wood"))
	for z in [-3.0, -9.0]:
		var o := OmniLight3D.new()
		o.light_color = Color(1.0, 0.6, 0.28)
		o.light_energy = 1.6
		o.omni_range = 5.5
		o.position = Vector3(0, 2.5, z)
		add_child(o)
		lamps.append(o)
	cam = Camera3D.new()
	cam.fov = 58.0
	cam.position = Vector3(0, 1.55, 2.0)
	cam.h_offset = -0.55
	cam.current = true
	add_child(cam)
	var fl := SpotLight3D.new()
	fl.light_color = Color(1.0, 0.93, 0.8)
	fl.light_energy = 2.0
	fl.spot_range = 14.0
	fl.spot_angle = 30.0
	fl.spot_angle_attenuation = 1.6
	cam.add_child(fl)
	ghost = CharacterBody3D.new()
	ghost.set_script(GhostScript)
	add_child(ghost)
	ghost.show_only()
	ghost.global_position = Vector3(0.0, 0.0, -10.0)
	ghost.rotation.y = 0.0     # faces -z (away); turned around below
	ghost.rotation.y = PI
	ghost._play("idle")

func _label(text: String, size: int, color: Color, fnt: Font = null) -> Label:
	var l := Label.new()
	l.text = text
	var ls := LabelSettings.new()
	ls.font = fnt if fnt else font
	ls.font_size = size
	ls.font_color = color
	ls.outline_size = int(size * 0.07)
	ls.outline_color = Color(0.1, 0.0, 0.0)
	ls.shadow_size = int(size * 0.1)
	ls.shadow_color = Color(0, 0, 0, 0.8)
	ls.shadow_offset = Vector2(4, 6)
	l.label_settings = ls
	return l

func _style(col: Color, border: Color, bw := 4) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = col
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(14)
	s.content_margin_left = 40
	s.content_margin_right = 40
	s.content_margin_top = 14
	s.content_margin_bottom = 14
	return s

func _button(text: String, size := 70) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(560, 124)
	b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	b.add_theme_font_override("font", font)
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", RED)
	b.add_theme_color_override("font_hover_color", Color(1.0, 0.12, 0.12))
	b.add_theme_color_override("font_pressed_color", Color(1.0, 0.3, 0.3))
	b.add_theme_color_override("font_outline_color", Color(0.1, 0, 0))
	b.add_theme_constant_override("outline_size", 6)
	b.add_theme_stylebox_override("normal", _style(Color(0.05, 0.0, 0.0, 0.72), Color(0.55, 0.0, 0.0)))
	b.add_theme_stylebox_override("hover", _style(Color(0.16, 0.0, 0.0, 0.8), RED))
	b.add_theme_stylebox_override("pressed", _style(Color(0.28, 0.0, 0.0, 0.9), Color(1.0, 0.15, 0.15)))
	b.add_theme_stylebox_override("focus", _style(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0))
	b.focus_mode = Control.FOCUS_NONE
	return b

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)
	root_ui = Control.new()
	root_ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layer.add_child(root_ui)
	# vignette
	var vg := ColorRect.new()
	vg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	vg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sh := Shader.new()
	sh.code = "shader_type canvas_item;\nvoid fragment(){ vec2 uv=UV-0.5; float v=smoothstep(0.25,0.95,length(uv*vec2(1.0,0.8))); float n=fract(sin(dot(floor(UV*vec2(540.0,300.0))+floor(TIME*24.0)*17.0,vec2(12.9898,78.233)))*43758.5453); COLOR=vec4(vec3(n)*0.3*step(0.5,n),max(v*0.78,0.05*n)); }"
	var sm := ShaderMaterial.new()
	sm.shader = sh
	vg.material = sm
	root_ui.add_child(vg)

	var mm := MarginContainer.new()
	mm.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mm.add_theme_constant_override("margin_left", 150)
	mm.add_theme_constant_override("margin_top", 40)
	mm.add_theme_constant_override("margin_bottom", 36)
	mm.add_theme_constant_override("margin_right", 150)
	root_ui.add_child(mm)
	main_box = mm
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 22)
	mm.add_child(col)
	var title := _label("CHAYA", 230, RED)
	col.add_child(title)
	if ResourceLoader.exists(FONT_DEV):
		var dv := _label("छाया", 80, Color(0.6, 0.02, 0.02), load(FONT_DEV))
		col.add_child(dv)
	var sp := Control.new()
	sp.custom_minimum_size = Vector2(0, 14)
	col.add_child(sp)
	var start := _button("START")
	start.pressed.connect(_on_start)
	col.add_child(start)
	var sett := _button("SETTINGS")
	sett.pressed.connect(_on_settings)
	col.add_child(sett)
	var fill := Control.new()
	fill.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(fill)
	var dev := _label("mxyan games", 44, Color(0.75, 0.08, 0.08))
	col.add_child(dev)

	# settings panel
	var sbox := Control.new()
	sbox.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sbox.visible = false
	root_ui.add_child(sbox)
	settings_box = sbox
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.78)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sbox.add_child(dim)
	var cen := CenterContainer.new()
	cen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sbox.add_child(cen)
	var sc := VBoxContainer.new()
	sc.add_theme_constant_override("separation", 34)
	cen.add_child(sc)
	var st := _label("SETTINGS", 130, RED)
	st.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sc.add_child(st)
	var sl := _label("SENSITIVITY", 64, Color(0.85, 0.1, 0.1))
	sl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sc.add_child(sl)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 24)
	sc.add_child(row)
	var minus := _button("-", 80)
	minus.custom_minimum_size = Vector2(130, 124)
	minus.pressed.connect(func(): _bump(-0.1))
	row.add_child(minus)
	_slider = HSlider.new()
	_slider.min_value = Settings.SENS_MIN
	_slider.max_value = Settings.SENS_MAX
	_slider.step = 0.05
	_slider.value = Settings.sensitivity
	_slider.custom_minimum_size = Vector2(440, 124)
	_slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var tr := _style(Color(0.12, 0.0, 0.0, 0.9), Color(0.5, 0.0, 0.0), 2)
	tr.content_margin_top = 14
	tr.content_margin_bottom = 14
	_slider.add_theme_stylebox_override("slider", tr)
	var ga := StyleBoxFlat.new()
	ga.bg_color = RED
	ga.set_corner_radius_all(10)
	ga.content_margin_top = 14
	ga.content_margin_bottom = 14
	_slider.add_theme_stylebox_override("grabber_area", ga)
	_slider.add_theme_stylebox_override("grabber_area_highlight", ga)
	var gi := _grabber_icon()
	_slider.add_theme_icon_override("grabber", gi)
	_slider.add_theme_icon_override("grabber_highlight", gi)
	_slider.add_theme_icon_override("grabber_disabled", gi)
	_slider.value_changed.connect(_on_slider)
	row.add_child(_slider)
	var plus := _button("+", 80)
	plus.custom_minimum_size = Vector2(130, 124)
	plus.pressed.connect(func(): _bump(0.1))
	row.add_child(plus)
	_sens_label = _label("", 54, Color(0.85, 0.1, 0.1))
	_sens_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sc.add_child(_sens_label)
	var back := _button("BACK")
	back.pressed.connect(_on_back)
	var cc := CenterContainer.new()
	cc.add_child(back)
	sc.add_child(cc)
	_update_sens_label()

	fade = ColorRect.new()
	fade.color = Color(0, 0, 0, 1)
	fade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root_ui.add_child(fade)
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 0.0, 1.4)

func _grabber_icon() -> ImageTexture:
	var n := 64
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in range(n):
		for x in range(n):
			var d := Vector2(x - n / 2.0 + 0.5, y - n / 2.0 + 0.5).length()
			var a := clampf(n / 2.0 - 1.0 - d, 0.0, 1.0)
			var rim := clampf(d - (n / 2.0 - 8.0), 0.0, 1.0)
			img.set_pixel(x, y, Color(0.95 - rim * 0.45, 0.1, 0.1, a))
	return ImageTexture.create_from_image(img)

func _update_sens_label() -> void:
	_sens_label.text = "%d%%" % int(round(Settings.sensitivity * 100.0))

func _on_slider(v: float) -> void:
	Settings.sensitivity = v
	Settings.save()
	_update_sens_label()

func _bump(d: float) -> void:
	_click()
	_slider.value = clampf(_slider.value + d, Settings.SENS_MIN, Settings.SENS_MAX)

func _click() -> void:
	Sfx.play("ui_click", -4.0)

func _on_settings() -> void:
	_click()
	main_box.visible = false
	settings_box.visible = true

func _on_back() -> void:
	_click()
	settings_box.visible = false
	main_box.visible = true

func _on_start() -> void:
	if _starting:
		return
	_starting = true
	_click()
	Sfx.play("menu_start", -2.0)
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 1.0, 0.9)
	await tw.finished
	get_tree().change_scene_to_file(GAME)

func _process(dt: float) -> void:
	_t += dt
	cam.position = Vector3(sin(_t * 0.31) * 0.05, 1.55 + sin(_t * 0.5) * 0.02, 2.0 - minf(_t * 0.02, 0.4))
	cam.rotation = Vector3(sin(_t * 0.23) * 0.01, sin(_t * 0.17) * 0.012, 0.0)
	for i in range(lamps.size()):
		var f := 0.85 + 0.1 * sin(_t * 9.0 + i * 3.0) + 0.05 * sin(_t * 23.0 + i)
		if _flick > 0.0:
			f *= 0.1 + 0.9 * float(randf() > 0.55)
		(lamps[i] as OmniLight3D).light_energy = 1.6 * f
	if _flick > 0.0:
		_flick -= dt
	_next_event -= dt
	if _next_event <= 0.0:
		_next_event = randf_range(8.0, 14.0)
		_flick = 0.9
		_step = (_step + 1) % 6
		# every flicker she is a little closer
		var z := -10.0 + float(_step) * 1.5
		get_tree().create_timer(0.7).timeout.connect(func(): ghost.global_position = Vector3(0, 0, z))
		Sfx.play("menu_sting", -8.0)
