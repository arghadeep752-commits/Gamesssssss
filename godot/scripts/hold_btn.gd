class_name HoldBtn
extends Control
## A button that knows when it is held down (pedals, fire) and when it is tapped. Works with several fingers at
## once (each touch is routed to the control it started on).

var held := false
var on_click := Callable()
var on_down := Callable()
var bg: Control
var icon: Control
var label: Label
var base_color := Color.WHITE
var _index := -99
var _start := Vector2.ZERO
var _moved := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_PASS
	process_mode = Node.PROCESS_MODE_ALWAYS


func _gui_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		if e.pressed and _index == -99:
			_index = e.index
			_start = e.position
			_moved = false
			_press()
			accept_event()
		elif not e.pressed and e.index == _index:
			var was := held
			_release()
			if was and not _moved and on_click.is_valid() and Rect2(Vector2.ZERO, size).has_point(e.position):
				if G.audio:
					G.audio.ui("ui_click", 0.5)
				on_click.call()
			accept_event()
	elif e is InputEventScreenDrag and e.index == _index:
		if e.position.distance_to(_start) > 40.0 and get_parent_control() is not HoldBtn and _in_scroll():
			_moved = true
			_release()


func _in_scroll() -> bool:
	var p := get_parent()
	while p:
		if p is ScrollContainer:
			return true
		p = p.get_parent()
	return false


func _press() -> void:
	held = true
	if bg:
		Ui.set_color(bg, base_color * 0.75 + Color(0, 0, 0, 0.25))
	scale = Vector2.ONE * 0.94
	if on_down.is_valid():
		on_down.call()


func _release() -> void:
	held = false
	_index = -99
	if bg:
		Ui.set_color(bg, base_color)
	scale = Vector2.ONE


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree():
		_release()


func set_color(c: Color) -> void:
	base_color = c
	if bg and not held:
		Ui.set_color(bg, c)
