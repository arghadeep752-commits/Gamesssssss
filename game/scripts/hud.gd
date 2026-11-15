class_name Hud
extends Control
## The in-game controls, laid out like Granny: the settings gear top-left, the combined stand/crouch button under
## it, the joystick bottom-left, the hand (interact) on the right, DROP written at the bottom while you hold
## something, and the name of whatever you are looking at under the centre dot. The icons are the game's own
## images in game/ui/, drawn slightly see-through. A circle marks what you can use: a bright one on the thing
## you are aiming at, faint ones on items lying nearby.

signal interact
signal drop
signal crouch
signal pause

var move := Vector2.ZERO
var look := Vector2.ZERO           # accumulated look drag, consumed by the player
var crouched := false
var label_text := ""
var can_interact := false
var holding := false
var message := ""
var message_t := 0.0
var day_text := ""
var font: Font
var font_title: Font
var font_scale := 1.0
var marks: Array = []              # [{"p": screen point, "main": bool}] things you can use
var _pulse := 0.0
const JOY_R := 78.0                # thumb travel for full speed (on a 720-pixel-high screen)

const UI_ALPHA := 0.78               # the whole HUD is a little see-through
var tex_knob: Texture2D = load("res://game/ui/knob.png")
var tex_ring: Texture2D = load("res://game/ui/ring.png")
var tex_crouch: Texture2D = load("res://game/ui/crouch.png")
var tex_stand: Texture2D = load("res://game/ui/stand.png")
var tex_gear: Texture2D = load("res://game/ui/gear.png")
var tex_hand: Texture2D = load("res://game/ui/hand.png")

var _joy_id := -1
var _joy_target := Vector2.ZERO     # where the stick points (after the dead zone and curve)
var _knob := Vector2.ZERO           # where the knob is drawn (follows the thumb)
var _joy_origin := Vector2.ZERO      # where the stick is while you hold it: under your thumb, not fixed
var _joy_pos := Vector2.ZERO
var _look_id := -1


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	resized.connect(_home_joy)


func _home_joy() -> void:
	if _joy_id == -1:
		_joy_origin = joy_center()


func u() -> float:
	return size.y / 720.0


func joy_center() -> Vector2:
	return Vector2(225 * u(), size.y - 210 * u())


func r_gear() -> Rect2:
	return Rect2(34 * u(), 26 * u(), 92 * u(), 92 * u())


func r_crouch() -> Rect2:
	return Rect2(24 * u(), 142 * u(), 112 * u(), 160 * u())


func r_hand() -> Rect2:
	return Rect2(size.x - 290 * u(), size.y * 0.33, 188 * u(), 170 * u())


func r_drop() -> Rect2:
	return Rect2(size.x / 2 - 135 * u(), size.y - 135 * u(), 270 * u(), 100 * u())


func _tex_in(t: Texture2D, r: Rect2, a: float) -> void:
	"""Draw t as large as fits in r, centred, keeping its proportions."""
	if t == null:
		return
	var ts := t.get_size()
	var k := minf(r.size.x / ts.x, r.size.y / ts.y)
	var sz := ts * k
	draw_texture_rect(t, Rect2(r.get_center() - sz / 2, sz), false, Color(1, 1, 1, a))


func show_message(t: String, secs := 2.5) -> void:
	message = t
	message_t = secs
	queue_redraw()


func reset_touches() -> void:
	_joy_id = -1
	_look_id = -1
	move = Vector2.ZERO
	_joy_target = Vector2.ZERO
	_knob = Vector2.ZERO
	look = Vector2.ZERO
	marks = []
	_joy_origin = joy_center()


func _process(dt: float) -> void:
	if message_t > 0.0:
		message_t -= dt
		if message_t <= 0.0:
			message = ""
		queue_redraw()
	_pulse += dt
	# keyboard (desktop testing)
	if _joy_id == -1:
		var k := Vector2(Input.get_axis(&"ui_left", &"ui_right"), Input.get_axis(&"ui_up", &"ui_down"))
		_joy_target = k
		_knob = _knob.lerp(Vector2.ZERO, 1.0 - exp(-dt * 18.0))
		_joy_origin = _joy_origin.lerp(joy_center(), 1.0 - exp(-dt * 18.0))
	move = _joy_target                 # the player eases its speed itself; a second easing here made it sluggish
	queue_redraw()


func _unhandled_input(e: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	if e is InputEventScreenTouch:
		var p: Vector2 = e.position
		if e.pressed:
			if r_gear().has_point(p):
				pause.emit()
			elif r_crouch().grow(10 * u()).has_point(p):
				crouch.emit()
			elif can_interact and r_hand().grow(14 * u()).has_point(p):
				interact.emit()
			elif holding and r_drop().grow(12 * u()).has_point(p):
				drop.emit()
			elif p.x < size.x * 0.4 and p.y > size.y * 0.3 and _joy_id == -1:
				# the stick starts where the thumb lands, so touching off-centre never jerks you forward
				_joy_id = e.index
				_joy_origin = joy_center() if p.distance_to(joy_center()) < 34 * u() else p
				_joy_pos = p
				_update_joy()
			elif _look_id == -1:
				_look_id = e.index
		else:
			if e.index == _joy_id:
				_joy_id = -1
				_joy_target = Vector2.ZERO
			if e.index == _look_id:
				_look_id = -1
		queue_redraw()
	elif e is InputEventScreenDrag:
		if e.index == _joy_id:
			_joy_pos = e.position
			_update_joy()
			queue_redraw()
		elif e.index == _look_id:
			look += e.relative
	elif e is InputEventKey and e.pressed and not e.echo:
		if e.keycode == KEY_E:
			interact.emit()
		elif e.keycode == KEY_Q:
			drop.emit()
		elif e.keycode == KEY_C:
			crouch.emit()


func _update_joy() -> void:
	var r := JOY_R * u()
	var off := _joy_pos - _joy_origin
	if off.length() > r:
		# past the rim the stick follows the thumb, so turning back responds at once
		_joy_origin = _joy_pos - off.normalized() * r
		off = off.normalized() * r
	var d := off / r
	_knob = d
	var m := d.length()
	if m < 0.08:
		_joy_target = Vector2.ZERO
	else:
		var t := clampf((m - 0.08) / 0.92, 0.0, 1.0)
		_joy_target = d / m * (t * t * (3.0 - 2.0 * t) * 0.35 + t * 0.65)      # gentle near the centre, full at the rim


func _draw() -> void:
	var s := u()
	# circles on the things you can use (a dark edge keeps them visible on white walls)
	var lab_at := Vector2(size.x / 2, size.y * 0.585)
	for m in marks:
		var main: bool = m["main"]
		var mp: Vector2 = m["p"]
		var rr := (30.0 + 2.5 * sin(_pulse * 5.0)) * s if main else 13.0 * s
		var wd := (3.0 if main else 2.0) * s
		draw_arc(mp, rr, 0, TAU, 48, Color(0, 0, 0, 0.35), wd + 2.5 * s, true)
		draw_arc(mp, rr, 0, TAU, 48, Color(1, 1, 1, UI_ALPHA * (0.95 if main else 0.6)), wd, true)
		if main:
			draw_arc(mp, rr + 7 * s, 0, TAU, 48, Color(1, 1, 1, UI_ALPHA * 0.25), 1.5 * s, true)
			# the name goes under the circle instead of over it
			lab_at = Vector2(clampf(mp.x, 160 * s, size.x - 160 * s), clampf(mp.y + rr + 52 * s, size.y * 0.4, size.y * 0.82))
	# joystick: the ring under your thumb (it glides back home when you let go), and the knob that follows it
	var jc := _joy_origin
	var ring_d := 262 * s
	draw_texture_rect(tex_ring, Rect2(jc - Vector2(ring_d, ring_d) / 2, Vector2(ring_d, ring_d)), false, Color(1, 1, 1, UI_ALPHA * 0.75))
	var knob_d := 162 * s
	var kc := jc + _knob * JOY_R * s
	draw_texture_rect(tex_knob, Rect2(kc - Vector2(knob_d, knob_d) / 2, Vector2(knob_d, knob_d)), false, Color(1, 1, 1, UI_ALPHA))
	# settings gear in its rounded box, the stand / crouch button under it
	var rg := r_gear()
	draw_style_box(_gear_box(), rg)
	_tex_in(tex_gear, rg.grow(-14 * s), UI_ALPHA)
	_tex_in(tex_crouch if crouched else tex_stand, r_crouch(), UI_ALPHA)
	if can_interact:
		_tex_in(tex_hand, r_hand(), UI_ALPHA)
	if font:
		if holding:
			_draw_drop(s)
		if label_text != "":
			var fs := int(40 * s * font_scale)
			var w := font.get_string_size(label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
			draw_string(font, Vector2(lab_at.x - w / 2 + 2 * s, lab_at.y + 2 * s), label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0, 0, 0, 0.45))
			draw_string(font, Vector2(lab_at.x - w / 2, lab_at.y), label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1, 1, 1, UI_ALPHA))
		if message != "":
			var fs2 := int(34 * s * font_scale)
			var w2 := font.get_string_size(message, HORIZONTAL_ALIGNMENT_LEFT, -1, fs2).x
			draw_string(font, Vector2(size.x / 2 - w2 / 2, size.y * 0.72), message, HORIZONTAL_ALIGNMENT_LEFT, -1, fs2, Color(1, 1, 1, UI_ALPHA * clampf(message_t, 0, 1)))
	# centre dot
	draw_arc(size / 2, 5 * s, 0, TAU, 24, Color(1, 1, 1, UI_ALPHA * 0.7), 1.6 * s, true)


var _box: StyleBoxFlat


func _gear_box() -> StyleBoxFlat:
	if _box == null:
		_box = StyleBoxFlat.new()
		_box.bg_color = Color(0, 0, 0, 0)
		_box.border_color = Color(1, 1, 1, UI_ALPHA * 0.9)
		_box.set_border_width_all(int(max(2.0, 3 * u())))
		_box.set_corner_radius_all(int(10 * u()))
	return _box


func _draw_drop(s: float) -> void:
	"""DROP written at the bottom, with a bigger first letter."""
	var r := r_drop()
	var big_fs := int(64 * s * font_scale)
	var small_fs := int(47 * s * font_scale)
	var w1 := font.get_string_size("D", HORIZONTAL_ALIGNMENT_LEFT, -1, big_fs).x
	var w2 := font.get_string_size("ROP", HORIZONTAL_ALIGNMENT_LEFT, -1, small_fs).x
	var x := r.get_center().x - (w1 + w2) / 2
	var base := r.position.y + r.size.y * 0.72
	var c := Color(1, 1, 1, UI_ALPHA)
	draw_string(font, Vector2(x, base), "D", HORIZONTAL_ALIGNMENT_LEFT, -1, big_fs, c)
	draw_string(font, Vector2(x + w1, base), "ROP", HORIZONTAL_ALIGNMENT_LEFT, -1, small_fs, c)


func refresh() -> void:
	queue_redraw()
