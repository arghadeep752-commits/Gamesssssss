extends Node3D
## A simple hinged door. The door node sits at the bottom-centre of the
## doorway. Local +X runs along the wall, the door swings towards local -Z.

const InteractScript = preload("res://scripts/interactable.gd")

var width := 1.0
var height := 2.2
var thickness := 0.05
var is_open := false
var locked := false
var lock_message := "It's locked."
var open_angle := deg_to_rad(100.0)
var floor_index := 0
var room_name := ""
var pivot: Node3D
var body: StaticBody3D
var waypoint_ids: Array = []  # AI points behind this door (disabled while locked)


func build(w: float, h: float, layer_mask: int) -> void:
	width = w
	height = h
	pivot = Node3D.new()
	pivot.name = "Hinge"
	pivot.position = Vector3(-w * 0.5, 0.0, 0.0)
	add_child(pivot)

	var slab_w := w - 0.04
	var slab_h := h - 0.03
	var center := Vector3(w * 0.5, slab_h * 0.5 + 0.01, 0.0)

	# Door slab (edges) with the wood texture.
	var slab := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(slab_w, slab_h, thickness)
	slab.mesh = bm
	slab.material_override = Assets.get_material("door")
	slab.position = center
	slab.layers = layer_mask
	pivot.add_child(slab)

	# Front and back pictures (your door texture is shown here).
	var face_mat := Assets.get_door_face_material()
	for side in [1.0, -1.0]:
		var q := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(slab_w, slab_h)
		q.mesh = qm
		q.material_override = face_mat
		q.position = center + Vector3(0, 0, side * (thickness * 0.5 + 0.002))
		if side < 0.0:
			q.rotation.y = PI
		q.layers = layer_mask
		pivot.add_child(q)

	# Raised panels so a plain wood texture still looks like a door.
	if not Assets.is_user_texture("door"):
		var panel_mat := Assets.get_material("door")
		for side in [1.0, -1.0]:
			for py in [0.28, 0.72]:
				var p := MeshInstance3D.new()
				var pm := BoxMesh.new()
				pm.size = Vector3(slab_w * 0.62, slab_h * 0.3, 0.02)
				p.mesh = pm
				p.material_override = panel_mat
				p.position = Vector3(w * 0.5, slab_h * py, side * (thickness * 0.5 + 0.012))
				p.layers = layer_mask
				pivot.add_child(p)

	# Door handles (metal, reflective).
	var metal := Assets.color_mat(Color(0.78, 0.72, 0.55), 0.25, 1.0)
	for side in [1.0, -1.0]:
		var hnd := MeshInstance3D.new()
		var hm := BoxMesh.new()
		hm.size = Vector3(0.14, 0.03, 0.03)
		hnd.mesh = hm
		hnd.material_override = metal
		hnd.position = Vector3(w - 0.14, 1.0, side * (thickness * 0.5 + 0.045))
		hnd.layers = layer_mask
		pivot.add_child(hnd)
		var base := MeshInstance3D.new()
		var bmesh := BoxMesh.new()
		bmesh.size = Vector3(0.05, 0.16, 0.02)
		base.mesh = bmesh
		base.material_override = metal
		base.position = Vector3(w - 0.1, 1.0, side * (thickness * 0.5 + 0.012))
		base.layers = layer_mask
		pivot.add_child(base)

	# Collision + interaction body (moves with the door).
	var ib = InteractScript.new()
	ib.kind = "door"
	ib.prompt = "Open"
	ib.target = self
	ib.collision_layer = 1 | 8
	ib.collision_mask = 0
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(slab_w, slab_h, thickness + 0.06)
	cs.shape = shape
	cs.position = center
	ib.add_child(cs)
	pivot.add_child(ib)
	body = ib


func get_prompt() -> String:
	if locked:
		return "Locked"
	return "Close" if is_open else "Open"


## Returns false if the door is locked.
func toggle() -> bool:
	if locked:
		return false
	set_open(not is_open)
	return true


func set_open(value: bool, quiet: bool = false) -> void:
	if value == is_open:
		return
	is_open = value
	var tw := create_tween()
	var target_angle := open_angle if value else 0.0
	tw.tween_property(pivot, "rotation:y", target_angle, 0.55).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	if quiet:
		return
	var pos := global_position + Vector3(0, 1.2, 0)
	if value:
		Assets.play_3d("door_open", pos, get_parent(), -2.0, randf_range(0.95, 1.05))
		if randf() < 0.5:
			Assets.play_3d("creak", pos, get_parent(), -6.0, randf_range(0.9, 1.1))
	else:
		Assets.play_3d("door_close", pos, get_parent(), -2.0, randf_range(0.95, 1.05))


func rattle() -> void:
	Assets.play_3d("locked", global_position + Vector3(0, 1.0, 0), get_parent(), 0.0)
	var tw := create_tween()
	tw.tween_property(pivot, "rotation:y", 0.03, 0.06)
	tw.tween_property(pivot, "rotation:y", -0.02, 0.06)
	tw.tween_property(pivot, "rotation:y", 0.0, 0.06)
