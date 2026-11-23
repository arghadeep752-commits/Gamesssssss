extends Control
## The small circle in the middle of the screen. Aim it at the door to use it.

@export var radius := 7.0


func _draw() -> void:
	var middle := size * 0.5
	draw_arc(middle, radius, 0.0, TAU, 40, Color(0, 0, 0, 0.45), 4.5, true)
	draw_arc(middle, radius, 0.0, TAU, 40, Color.WHITE, 2.2, true)
