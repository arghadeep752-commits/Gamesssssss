class_name Stick
extends Control
## The movement joystick: appears where the thumb lands in its zone (left part of the screen).

var base_rt: Control
var knob: Control
var value := Vector2.ZERO
var home := Vector2.ZERO
var _index := -99
const RADIUS := 120.0


func setup(b: Control, k: Control) -> void:
	base_rt = b
	knob = k
	home = b.position
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		if e.pressed and _index == -99:
			_index = e.index
			base_rt.position = e.position - base_rt.size * 0.5
			_drag(e.position)
			accept_event()
		elif not e.pressed and e.index == _index:
			_reset()
			accept_event()
	elif e is InputEventScreenDrag and e.index == _index:
		_drag(e.position)
		accept_event()


func _drag(p: Vector2) -> void:
	var c := base_rt.position + base_rt.size * 0.5
	var v := (p - c).limit_length(RADIUS)
	knob.position = base_rt.size * 0.5 + v - knob.size * 0.5
	value = Vector2(v.x, -v.y) / RADIUS          # y up, like the Unity version
	if value.length() < 0.12:
		value = Vector2.ZERO


func _reset() -> void:
	_index = -99
	value = Vector2.ZERO
	if knob:
		knob.position = base_rt.size * 0.5 - knob.size * 0.5
	if base_rt:
		base_rt.position = home


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree():
		_reset()
