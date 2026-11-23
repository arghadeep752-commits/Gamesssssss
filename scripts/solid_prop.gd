extends Node3D
## A piece of furniture you can't walk through: puts a box collider around its 3D model ($Model).


func _ready() -> void:
	var box := mesh_box(self, $Model)
	var body := StaticBody3D.new()
	add_child(body)
	body.position = box.get_center()
	var shape := BoxShape3D.new()
	shape.size = box.size
	var collider := CollisionShape3D.new()
	collider.shape = shape
	body.add_child(collider)


## Box around all meshes under `model`, measured in `space`'s own coordinates.
static func mesh_box(space: Node3D, model: Node, name_filter := "") -> AABB:
	var to_space := space.global_transform.affine_inverse()
	var box := AABB()
	var first := true
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		if name_filter != "" and not String(mesh.name).contains(name_filter):
			continue
		var part: AABB = (to_space * mesh.global_transform) * mesh.get_aabb()
		box = part if first else box.merge(part)
		first = false
	return box
