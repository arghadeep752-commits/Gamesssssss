extends CanvasLayer
## Touch controls: a floating joystick (left side), a run button (bottom right) and look-by-dragging
## (right side), the screen effects (vignette, grain), the list of ritual items to find, and the tutorial's
## prompts and pointers.

signal look(delta: Vector2)

var move_vec := Vector2.ZERO
var run_held := false

var _size := Vector2(1920, 1080)
var _layer: Control
var _fx: ColorRect
var _fx_mat: ShaderMaterial

# joystick
var _joy_touch := -1
var _joy_base := Vector2.ZERO
var _joy_knob := Vector2.ZERO
const JOY_R := 180.0          # bigger joystick (canvas is 1080 px tall)
const KNOB_R := 82.0
# run
var _run_touch := -1
var _run_center := Vector2.ZERO
const RUN_R := 128.0
var _tex_ring: Texture2D = preload("res://assets/ui/joy_ring.png")
var _tex_knob: Texture2D = preload("res://assets/ui/joy_knob.png")
var _tex_run: Texture2D = preload("res://assets/ui/run_button.png")
# look
var _look_touch := -1

# item list, prompts, tutorial pointers
const FONT_GAME := "res://assets/fonts/TheFriendlyIndians.ttf"
const FONT_UI := "res://assets/downloaded/fonts/Rajdhani-Bold.ttf"
const ITEM_NAMES := {"kalash": "KALASH", "diya": "DIYA", "coconut": "COCONUT", "kumkum": "KUMKUM", "kapoor": "KAPOOR", "gangajal": "GANGAJAL"}
var _font: Font
var _list_panel: PanelContainer
var _list_cells := {}
var _list_title: Label
var _list_tw: Tween
var _prompt_panel: PanelContainer
var _prompt_label: Label
var _prompt_tw: Tween
var highlight := ""              # "joy", "run", "look" or "" - a pulsing ring for the tutorial
var guide_on := false
var guide_screen := Vector2.ZERO
var guide_visible := true
var _pulse := 0.0

var danger := 0.0 : set = _set_danger
var flash := 0.0 : set = _set_flash
var fade := 0.0 : set = _set_fade
var grain := 0.06

const FX_SHADER := """
shader_type canvas_item;
uniform float vignette = 0.62;
uniform float grain = 0.06;
uniform float danger = 0.0;
uniform float flash = 0.0;
uniform float fade = 0.0;
void fragment() {
	vec2 uv = UV - 0.5;
	float r = length(uv * vec2(1.0, 0.8));
	float v = smoothstep(0.30, 0.92, r);
	float n = fract(sin(dot(floor(UV * vec2(540.0, 300.0)) + floor(TIME * 24.0) * 17.0, vec2(12.9898, 78.233))) * 43758.5453);
	vec3 col = mix(vec3(0.0), vec3(0.55, 0.0, 0.0), danger * smoothstep(0.15, 1.0, r));
	float a = clamp(v * vignette + danger * 0.18 * v, 0.0, 1.0);
	col = mix(col, vec3(n), grain * 0.5);
	a = max(a, grain * 0.7 * (0.5 + n * 0.5));
	col = mix(col, vec3(1.0, 0.92, 0.85), flash);
	a = max(a, flash);
	col = mix(col, vec3(0.0), fade);
	a = max(a, fade);
	COLOR = vec4(col, a);
}
"""

func _ready() -> void:
	layer = 10
	_fx = ColorRect.new()
	_fx.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fx.set_anchors_preset(Control.PRESET_FULL_RECT)
	var sh := Shader.new()
	sh.code = FX_SHADER
	_fx_mat = ShaderMaterial.new()
	_fx_mat.shader = sh
	_fx.material = _fx_mat
	add_child(_fx)
	_layer = Control.new()
	_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	_layer.draw.connect(_draw_controls)
	add_child(_layer)
	get_viewport().size_changed.connect(_layout)
	_build_texts()
	_layout()

func _layout() -> void:
	_size = get_viewport().get_visible_rect().size
	_run_center = Vector2(_size.x - 270.0, _size.y - 260.0)
	_place_texts()
	if _joy_touch == -1:
		_joy_base = Vector2(300.0, _size.y - 290.0)
		_joy_knob = _joy_base
	_layer.queue_redraw()

func _set_danger(v: float) -> void:
	danger = v
	if _fx_mat: _fx_mat.set_shader_parameter("danger", v)

func _set_flash(v: float) -> void:
	flash = v
	if _fx_mat: _fx_mat.set_shader_parameter("flash", v)

func _set_fade(v: float) -> void:
	fade = v
	if _fx_mat: _fx_mat.set_shader_parameter("fade", v)

func hide_controls() -> void:
	_layer.visible = false

func show_controls() -> void:
	_layer.visible = true
	reset_touches()

func _process(dt: float) -> void:
	if highlight != "" or guide_on:
		_pulse += dt
		_layer.queue_redraw()

# ------------------------------------------------------------------------------------------ texts: item list, prompts

func _load_font() -> Font:
	var fb: Font = load(FONT_UI) if ResourceLoader.exists(FONT_UI) else ThemeDB.fallback_font
	if ResourceLoader.exists(FONT_GAME):
		var ff = load(FONT_GAME)
		if ff is FontFile:
			(ff as FontFile).fallbacks = [fb]
			var fv := FontVariation.new()
			fv.base_font = ff
			fv.spacing_glyph = 2
			return fv
	return fb

func _panel_style(alpha: float) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.04, 0.0, 0.0, alpha)
	sb.border_color = Color(0.5, 0.08, 0.04, alpha)
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(18)
	sb.content_margin_left = 34
	sb.content_margin_right = 34
	sb.content_margin_top = 18
	sb.content_margin_bottom = 20
	return sb

func _text(t: String, size: int, col: Color) -> Label:
	var l := Label.new()
	l.text = t
	var ls := LabelSettings.new()
	ls.font = _font
	ls.font_size = size
	ls.font_color = col
	ls.outline_size = maxi(4, int(size * 0.12))
	ls.outline_color = Color(0.05, 0.0, 0.0)
	ls.shadow_size = 6
	ls.shadow_color = Color(0, 0, 0, 0.7)
	l.label_settings = ls
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func _build_texts() -> void:
	_font = _load_font()
	# the list of ritual items
	_list_panel = PanelContainer.new()
	_list_panel.add_theme_stylebox_override("panel", _panel_style(0.62))
	_list_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_list_panel.modulate.a = 0.0
	_list_panel.visible = false
	add_child(_list_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_list_panel.add_child(v)
	_list_title = _text("FIND THESE ITEMS FOR THE RITUAL", 50, Color(1.0, 0.78, 0.45))
	v.add_child(_list_title)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(row)
	for id in ["kalash", "diya", "coconut", "kumkum", "kapoor", "gangajal"]:
		var cell := VBoxContainer.new()
		cell.custom_minimum_size = Vector2(196, 0)
		cell.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var icon := TextureRect.new()
		icon.custom_minimum_size = Vector2(150, 150)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var ip := "res://assets/map/icons/%s.png" % id
		if ResourceLoader.exists(ip):
			icon.texture = load(ip)
		cell.add_child(icon)
		var nm := _text(ITEM_NAMES[id], 38, Color(0.95, 0.88, 0.8))
		cell.add_child(nm)
		row.add_child(cell)
		_list_cells[id] = {"cell": cell, "icon": icon, "name": nm}
	# prompt banner (tutorial and the few messages of the game)
	_prompt_panel = PanelContainer.new()
	_prompt_panel.add_theme_stylebox_override("panel", _panel_style(0.55))
	_prompt_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_panel.modulate.a = 0.0
	_prompt_panel.visible = false
	add_child(_prompt_panel)
	_prompt_label = _text("", 54, Color(1.0, 0.86, 0.7))
	_prompt_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_prompt_label.custom_minimum_size = Vector2(1300, 0)
	_prompt_panel.add_child(_prompt_label)

func _place_texts() -> void:
	if _list_panel == null:
		return
	_list_panel.reset_size()
	var ls := _list_panel.get_combined_minimum_size()
	_list_panel.position = Vector2((_size.x - ls.x) / 2.0, 70.0)
	_prompt_panel.reset_size()
	var ps := _prompt_panel.get_combined_minimum_size()
	_prompt_panel.position = Vector2((_size.x - ps.x) / 2.0, _size.y * 0.5 - ps.y - 40.0)

## Show the six items; `found` ids are dimmed and ticked. hold <= 0: stay until hide_item_list().
func show_item_list(found: Dictionary, hold := 6.0, title := "FIND THESE ITEMS FOR THE RITUAL") -> void:
	_list_title.text = title
	for id in _list_cells:
		var c: Dictionary = _list_cells[id]
		var got: bool = found.has(id)
		(c["icon"] as TextureRect).modulate = Color(0.35, 0.35, 0.35, 0.55) if got else Color(1, 1, 1, 1)
		(c["name"] as Label).text = ("FOUND" if got else ITEM_NAMES[id])
		(c["name"] as Label).label_settings.font_color = Color(0.45, 0.85, 0.4) if got else Color(0.95, 0.88, 0.8)
	_list_panel.visible = true
	_place_texts()
	if _list_tw:
		_list_tw.kill()
	_list_tw = create_tween()
	_list_tw.tween_property(_list_panel, "modulate:a", 1.0, 0.45)
	if hold > 0.0:
		_list_tw.tween_interval(hold)
		_list_tw.tween_property(_list_panel, "modulate:a", 0.0, 0.7)
		_list_tw.tween_callback(func(): _list_panel.visible = false)

func hide_item_list() -> void:
	if _list_tw:
		_list_tw.kill()
	_list_tw = create_tween()
	_list_tw.tween_property(_list_panel, "modulate:a", 0.0, 0.5)
	_list_tw.tween_callback(func(): _list_panel.visible = false)

## A message in the middle of the screen. hold <= 0: stays until the next prompt or hide_prompt().
func prompt(text: String, hold := 0.0) -> void:
	_prompt_label.text = text
	_prompt_panel.visible = true
	_place_texts()
	if _prompt_tw:
		_prompt_tw.kill()
	_prompt_tw = create_tween()
	_prompt_tw.tween_property(_prompt_panel, "modulate:a", 1.0, 0.35)
	if hold > 0.0:
		_prompt_tw.tween_interval(hold)
		_prompt_tw.tween_property(_prompt_panel, "modulate:a", 0.0, 0.5)
		_prompt_tw.tween_callback(func(): _prompt_panel.visible = false)

func hide_prompt() -> void:
	if _prompt_tw:
		_prompt_tw.kill()
	_prompt_tw = create_tween()
	_prompt_tw.tween_property(_prompt_panel, "modulate:a", 0.0, 0.4)
	_prompt_tw.tween_callback(func(): _prompt_panel.visible = false)

func reset_touches() -> void:
	_joy_touch = -1
	_run_touch = -1
	_look_touch = -1
	move_vec = Vector2.ZERO
	run_held = false
	_layout()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var e := event as InputEventScreenTouch
		if e.pressed:
			if _run_touch == -1 and e.position.distance_to(_run_center) <= RUN_R * 1.35:
				_run_touch = e.index
				run_held = true
			elif _joy_touch == -1 and e.position.x < _size.x * 0.45:
				_joy_touch = e.index
				_joy_base = Vector2(clampf(e.position.x, JOY_R, _size.x * 0.45), clampf(e.position.y, JOY_R, _size.y - JOY_R))
				_joy_knob = e.position
				_update_joy(e.position)
			elif _look_touch == -1 and e.position.x >= _size.x * 0.3:
				_look_touch = e.index
		else:
			if e.index == _run_touch:
				_run_touch = -1
				run_held = false
			elif e.index == _joy_touch:
				_joy_touch = -1
				move_vec = Vector2.ZERO
				_joy_base = Vector2(300.0, _size.y - 290.0)
				_joy_knob = _joy_base
			elif e.index == _look_touch:
				_look_touch = -1
		_layer.queue_redraw()
	elif event is InputEventScreenDrag:
		var d := event as InputEventScreenDrag
		if d.index == _joy_touch:
			_update_joy(d.position)
		elif d.index == _look_touch:
			look.emit(d.relative)
		_layer.queue_redraw()

func _update_joy(p: Vector2) -> void:
	var travel := JOY_R * 0.62          # the knob stays inside the ring
	var off := p - _joy_base
	if off.length() > travel:
		off = off.normalized() * travel
	_joy_knob = _joy_base + off
	var v := off / travel
	move_vec = v if v.length() > 0.12 else Vector2.ZERO

func _draw_controls() -> void:
	var active := _joy_touch != -1
	# joystick: the orange ring and knob (player-supplied art), see-through
	var ring_a := 0.62 if active else 0.38
	_layer.draw_texture_rect(_tex_ring, Rect2(_joy_base - Vector2(JOY_R, JOY_R), Vector2(JOY_R, JOY_R) * 2.0), false, Color(1, 1, 1, ring_a))
	var kr := KNOB_R * (1.06 if active else 1.0)
	_layer.draw_texture_rect(_tex_knob, Rect2(_joy_knob - Vector2(kr, kr), Vector2(kr, kr) * 2.0), false, Color(1, 1, 1, 0.72 if active else 0.45))
	# run button: the running woman in a saree
	var rr := RUN_R * (0.93 if run_held else 1.0)
	_layer.draw_texture_rect(_tex_run, Rect2(_run_center - Vector2(rr, rr), Vector2(rr, rr) * 2.0), false, Color(1, 1, 1, 0.7 if run_held else 0.42))
	# tutorial: a pulsing ring round the control to use
	if highlight != "":
		var k := 0.5 + 0.5 * sin(_pulse * 5.0)
		var col := Color(1.0, 0.75, 0.3, 0.45 + 0.4 * k)
		match highlight:
			"joy":
				_layer.draw_arc(_joy_base, JOY_R * (1.12 + 0.1 * k), 0.0, TAU, 64, col, 7.0, true)
			"run":
				_layer.draw_arc(_run_center, RUN_R * (1.12 + 0.1 * k), 0.0, TAU, 64, col, 7.0, true)
			"look":
				var c := Vector2(_size.x * 0.66, _size.y * 0.42)
				var sw := sin(_pulse * 2.4) * 120.0
				_layer.draw_circle(c + Vector2(sw, 0), 42.0, Color(1.0, 0.75, 0.3, 0.35 + 0.3 * k))
				_layer.draw_line(c + Vector2(-200, 0), c + Vector2(200, 0), Color(1.0, 0.75, 0.3, 0.4), 5.0, true)
				for sgn in [-1.0, 1.0]:
					var tip := c + Vector2(220.0 * sgn, 0)
					_layer.draw_line(tip, tip + Vector2(-30.0 * sgn, -24), Color(1.0, 0.75, 0.3, 0.6), 6.0, true)
					_layer.draw_line(tip, tip + Vector2(-30.0 * sgn, 24), Color(1.0, 0.75, 0.3, 0.6), 6.0, true)
	# tutorial: a chevron at the edge of the screen pointing at the guiding light when it is off screen
	if guide_on and not guide_visible:
		var cen := _size / 2.0
		var dir := (guide_screen - cen)
		if dir.length() < 1.0:
			dir = Vector2(0, -1)
		dir = dir.normalized()
		var r := minf(_size.x * 0.42, _size.y * 0.38)
		var p := cen + Vector2(dir.x * _size.x * 0.42, dir.y * _size.y * 0.38).limit_length(maxf(r, 1.0) * 2.0)
		var k2 := 0.5 + 0.5 * sin(_pulse * 6.0)
		var col2 := Color(1.0, 0.8, 0.4, 0.55 + 0.4 * k2)
		var side := Vector2(-dir.y, dir.x)
		var pts := PackedVector2Array([p + dir * 46.0, p - dir * 10.0 + side * 34.0, p + dir * 6.0, p - dir * 10.0 - side * 34.0])
		_layer.draw_colored_polygon(pts, col2)
