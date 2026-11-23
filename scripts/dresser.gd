extends Node3D
## Chest of drawers ($Model, made in Blender by tools/blender/make_furniture.py).
## Every drawer slides open with USE and shut again.

const DrawerScript := preload("res://scripts/drawer.gd")
const SolidProp := preload("res://scripts/solid_prop.gd")
const FRONT_RECESS := 0.05   # the body's collider stays behind the drawer fronts, so you can aim at them

## How far a drawer comes out (metres).
@export var open_distance := 0.28
## Real recording of a wooden drawer sliding.
@export var slide_sound: AudioStream


func _ready() -> void:
	var model: Node3D = $Model
	var sound := AudioStreamPlayer3D.new()
	sound.stream = slide_sound
	sound.unit_size = 4.0
	add_child(sound)

	var drawers: Array[Node3D] = []
	var name_check := RegEx.create_from_string("^Drawer\\d+$")
	for node: Node3D in model.find_children("Drawer*", "Node3D", true, false):
		if name_check.search(node.name):
			drawers.append(node)

	# the front is where the handles stick out
	var front := Vector3.ZERO
	for drawer in drawers:
		var handle := SolidProp.mesh_box(self, drawer, "Knob")
		var body := SolidProp.mesh_box(self, drawer, "Box")
		front += handle.get_center() - body.get_center()
	front.y = 0.0
	front = Vector3(signf(front.x), 0, 0) if absf(front.x) > absf(front.z) else Vector3(0, 0, signf(front.z))

	# the dresser body (without the drawers)
	var frame := SolidProp.mesh_box(self, model, "Frame")
	if front.x > 0.5:
		frame.size.x -= FRONT_RECESS
	elif front.x < -0.5:
		frame.position.x += FRONT_RECESS
		frame.size.x -= FRONT_RECESS
	elif front.z > 0.5:
		frame.size.z -= FRONT_RECESS
	else:
		frame.position.z += FRONT_RECESS
		frame.size.z -= FRONT_RECESS
	_add_box(StaticBody3D.new(), frame)

	# one sliding collider per drawer; the drawer's model moves with it
	var pull := global_basis * (front * open_distance)
	for drawer in drawers:
		var body := DrawerScript.new()
		_add_box(body, SolidProp.mesh_box(self, drawer))
		body.setup(drawer, pull, sound)


func _add_box(body: Node3D, box: AABB) -> void:
	add_child(body)
	body.position = box.get_center()
	var shape := BoxShape3D.new()
	shape.size = box.size
	var collider := CollisionShape3D.new()
	collider.shape = shape
	body.add_child(collider)
