class_name Hud
extends Control
## The in-game controls, laid out like Granny: a white joystick bottom-left, the combined stand/crouch button
## top-left, the settings gear top-centre, the hand (interact) and drop buttons on the right, and the name of
## whatever you are looking at in the middle. Everything is drawn here with plain white shapes.

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
var peek := 0.0                     # 1 while hiding in an almirah: you look out through the gap of its doors
var font: Font
var font_title: Font
var font_scale := 1.0

var _joy_id := -1
var _joy_origin := Vector2.ZERO
var _joy_pos := Vector2.ZERO
var _look_id := -1
const WHITE := Color(1, 1, 1, 0.9)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func u() -> float:
	return size.y / 720.0


func joy_center() -> Vector2:
	return Vector2(150 * u(), size.y - 150 * u())


func r_crouch() -> Rect2:
	return Rect2(28 * u(), 24 * u(), 84 * u(), 110 * u())


func r_gear() -> Rect2:
	return Rect2(size.x / 2 - 40 * u(), 14 * u(), 80 * u(), 80 * u())


func r_hand() -> Rect2:
	return Rect2(size.x - 190 * u(), size.y - 330 * u(), 130 * u(), 130 * u())


func r_drop() -> Rect2:
	return Rect2(size.x - 175 * u(), size.y - 170 * u(), 100 * u(), 100 * u())


func show_message(t: String, secs := 2.5) -> void:
	message = t
	message_t = secs
	queue_redraw()


func reset_touches() -> void:
	_joy_id = -1
	_look_id = -1
	move = Vector2.ZERO
	look = Vector2.ZERO


func _process(dt: float) -> void:
	if message_t > 0.0:
		message_t -= dt
		if message_t <= 0.0:
			message = ""
		queue_redraw()
	# keyboard (desktop testing)
	if _joy_id == -1:
		var k := Vector2(Input.get_axis(&"ui_left", &"ui_right"), Input.get_axis(&"ui_up", &"ui_down"))
		move = k


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
				_joy_id = e.index
				_joy_origin = joy_center()
				_joy_pos = p
				_update_joy()
			elif _look_id == -1:
				_look_id = e.index
		else:
			if e.index == _joy_id:
				_joy_id = -1
				move = Vector2.ZERO
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
	var d := (_joy_pos - _joy_origin) / (90.0 * u())
	if d.length() > 1.0:
		d = d.normalized()
	move = d if d.length() > 0.12 else Vector2.ZERO


func _capsule(a: Vector2, b: Vector2, w: float, c: Color) -> void:
	draw_line(a, b, c, w, true)
	draw_circle(a, w * 0.5, c)
	draw_circle(b, w * 0.5, c)


func _draw_person(r: Rect2, crouching: bool) -> void:
	var s := r.size.y / 110.0
	var o := r.position + Vector2(r.size.x / 2, 0)
	if not crouching:
		draw_circle(o + Vector2(0, 14) * s, 11 * s, WHITE)
		_capsule(o + Vector2(0, 34) * s, o + Vector2(0, 62) * s, 22 * s, WHITE)
		_capsule(o + Vector2(-17, 34) * s, o + Vector2(-19, 62) * s, 8 * s, WHITE)
		_capsule(o + Vector2(17, 34) * s, o + Vector2(19, 62) * s, 8 * s, WHITE)
		_capsule(o + Vector2(-6, 68) * s, o + Vector2(-7, 104) * s, 10 * s, WHITE)
		_capsule(o + Vector2(6, 68) * s, o + Vector2(7, 104) * s, 10 * s, WHITE)
	else:
		draw_circle(o + Vector2(8, 40) * s, 11 * s, WHITE)
		_capsule(o + Vector2(2, 58) * s, o + Vector2(-10, 80) * s, 22 * s, WHITE)
		_capsule(o + Vector2(10, 60) * s, o + Vector2(22, 76) * s, 8 * s, WHITE)
		_capsule(o + Vector2(-8, 86) * s, o + Vector2(14, 84) * s, 10 * s, WHITE)
		_capsule(o + Vector2(14, 84) * s, o + Vector2(10, 104) * s, 10 * s, WHITE)
		_capsule(o + Vector2(-14, 92) * s, o + Vector2(-2, 104) * s, 10 * s, WHITE)


func _draw_hand(r: Rect2, c: Color) -> void:
	var s := r.size.x / 130.0
	var o := r.position
	var palm := PackedVector2Array([o + Vector2(36, 70) * s, o + Vector2(98, 66) * s, o + Vector2(98, 100) * s, o + Vector2(84, 122) * s,
		o + Vector2(52, 122) * s, o + Vector2(36, 100) * s])
	draw_colored_polygon(palm, c)
	var fingers := [[Vector2(44, 72), Vector2(40, 30)], [Vector2(60, 68), Vector2(59, 14)], [Vector2(76, 68), Vector2(78, 18)],
		[Vector2(91, 72), Vector2(96, 34)]]
	for f in fingers:
		_capsule(o + f[0] * s, o + f[1] * s, 13 * s, c)
	_capsule(o + Vector2(40, 100) * s, o + Vector2(16, 74) * s, 14 * s, c)


func _draw_gear(r: Rect2) -> void:
	var c := r.get_center()
	var s := r.size.x / 80.0
	for k in 8:
		var a := TAU * k / 8.0
		var d := Vector2(cos(a), sin(a))
		draw_line(c + d * 14 * s, c + d * 25 * s, WHITE, 10 * s, true)
	draw_circle(c, 18 * s, WHITE)
	draw_circle(c, 8 * s, Color(0, 0, 0, 0.75))


func _draw_peek() -> void:
	var w := size.x
	var h := size.y
	var gap := w * 0.16
	var l := (w - gap) / 2.0
	var a := clampf(peek, 0.0, 1.0)
	var dark := Color(0.01, 0.01, 0.012, 0.97 * a)
	draw_rect(Rect2(0, 0, l, h), dark)
	draw_rect(Rect2(l + gap, 0, w - l - gap, h), dark)
	for k in 6:                      # soft edges of the steel doors
		var f := float(k + 1) / 7.0
		var c := Color(0.01, 0.01, 0.012, 0.75 * a * (1.0 - f))
		draw_rect(Rect2(l + k * gap * 0.05, 0, gap * 0.05, h), c)
		draw_rect(Rect2(l + gap - (k + 1) * gap * 0.05, 0, gap * 0.05, h), c)
	draw_rect(Rect2(l, 0, gap, h * 0.06), Color(0.01, 0.01, 0.012, 0.6 * a))
	draw_rect(Rect2(l, h * 0.94, gap, h * 0.06), Color(0.01, 0.01, 0.012, 0.6 * a))


func _draw() -> void:
	var s := u()
	if peek > 0.01:
		_draw_peek()
	# joystick
	var jc := joy_center()
	draw_arc(jc, 92 * s, 0, TAU, 64, Color(1, 1, 1, 0.55), 4 * s, true)
	draw_circle(jc + move * 62 * s, 44 * s, Color(1, 1, 1, 0.85))
	_draw_person(r_crouch(), crouched)
	_draw_gear(r_gear())
	if can_interact:
		_draw_hand(r_hand(), WHITE)
	if holding:
		var r := r_drop()
		var c := r.get_center()
		draw_arc(c, 46 * s, 0, TAU, 48, WHITE, 4 * s, true)
		draw_line(c + Vector2(0, -24) * s, c + Vector2(0, 14) * s, WHITE, 8 * s, true)
		draw_colored_polygon(PackedVector2Array([c + Vector2(-18, 4) * s, c + Vector2(18, 4) * s, c + Vector2(0, 26) * s]), WHITE)
	if font:
		if label_text != "":
			var fs := int(34 * s * font_scale)
			var w := font.get_string_size(label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
			draw_string(font, Vector2(size.x / 2 - w / 2, size.y * 0.69), label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1, 1, 1, 0.95))
		if message != "":
			var fs2 := int(30 * s * font_scale)
			var w2 := font.get_string_size(message, HORIZONTAL_ALIGNMENT_LEFT, -1, fs2).x
			draw_string(font, Vector2(size.x / 2 - w2 / 2, size.y * 0.8), message, HORIZONTAL_ALIGNMENT_LEFT, -1, fs2, Color(1, 1, 1, clampf(message_t, 0, 1)))
		if day_text != "":
			var fs3 := int(28 * s * font_scale)
			var w3 := font.get_string_size(day_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs3).x
			draw_string(font, Vector2(size.x - w3 - 40 * s, 54 * s), day_text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs3, Color(1, 1, 1, 0.85))
	# centre dot
	draw_circle(size / 2, 2.5 * s, Color(1, 1, 1, 0.6))


func refresh() -> void:
	queue_redraw()
