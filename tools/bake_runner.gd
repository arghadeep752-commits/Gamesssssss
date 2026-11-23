extends SceneTree
## Runs tools/bake_room_reflection.gd (see that file for how to use it).


func _initialize() -> void:
	root.add_child(load("res://tools/bake_room_reflection.gd").new())
