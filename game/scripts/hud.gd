extends CanvasLayer
## Touch controls: a floating joystick (left side), a run button (bottom right) and look-by-dragging
## (right side). Nothing else is drawn - no text, no icons - apart from the screen effects (vignette, grain).

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
	_layout()

func _layout() -> void:
	_size = get_viewport().get_visible_rect().size
	_run_center = Vector2(_size.x - 270.0, _size.y - 260.0)
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
	# joystick: the orange ring and knob (player-supplied art) over a soft dark disc
	_layer.draw_circle(_joy_base, JOY_R * 0.93, Color(0.0, 0.0, 0.0, 0.22))
	var ring_a := 1.0 if active else 0.72
	_layer.draw_texture_rect(_tex_ring, Rect2(_joy_base - Vector2(JOY_R, JOY_R), Vector2(JOY_R, JOY_R) * 2.0), false, Color(1, 1, 1, ring_a))
	var kr := KNOB_R * (1.06 if active else 1.0)
	_layer.draw_texture_rect(_tex_knob, Rect2(_joy_knob - Vector2(kr, kr), Vector2(kr, kr) * 2.0), false, Color(1, 1, 1, 1.0 if active else 0.85))
	# run button: the running woman in a saree
	var rr := RUN_R * (0.93 if run_held else 1.0)
	_layer.draw_circle(_run_center, rr * 0.95, Color(0.0, 0.0, 0.0, 0.38 if run_held else 0.24))
	_layer.draw_texture_rect(_tex_run, Rect2(_run_center - Vector2(rr, rr), Vector2(rr, rr) * 2.0), false, Color(1, 1, 1, 1.0 if run_held else 0.8))
