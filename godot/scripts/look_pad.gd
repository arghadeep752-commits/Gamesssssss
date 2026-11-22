class_name LookPad
extends Control
## Dragging anywhere else on the screen turns the camera.

var _index := -99


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		if e.pressed and _index == -99:
			_index = e.index
		elif not e.pressed and e.index == _index:
			_index = -99
	elif e is InputEventScreenDrag and e.index == _index and G.cam:
		var k := 1080.0 / maxf(1.0, get_viewport_rect().size.y)
		G.cam.look += Vector2(e.relative.x, -e.relative.y) * k


func _notification(what: int) -> void:
	if what == NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree():
		_index = -99
