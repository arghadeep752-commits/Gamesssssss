class_name Human
extends CharacterBody3D
## Anyone with a body: the player, people on the street, the police.

static var all: Array = []

var rig: Rig
var model := ""
var tint := Color.WHITE
var health := 100.0
var max_health := 100.0
var armor := 0.0
var dead := false
var police := false
var is_player := false
var vehicle: Vehicle = null
var weapon := Combat.FIST
var weapon_node: Node3D = null
var muzzle_node: Node3D = null
var knocked := 0.0
var dead_time := 0.0
var looted := false
var blob: MeshInstance3D
var body_shape: CollisionShape3D


func _enter_tree() -> void:
	if not all.has(self):
		all.append(self)


func _exit_tree() -> void:
	all.erase(self)


func make_body(layer: int, mask: int, step_ray := false) -> void:
	collision_layer = layer
	collision_mask = mask
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	body_shape = CollisionShape3D.new()
	if step_ray:
		# capsule held up by a ray, so the body steps up kerbs and stairs like Unity's character controller
		cap.height = 1.3
		body_shape.shape = cap
		body_shape.position = Vector3(0, 0.45 + 0.65, 0)
		var ray := SeparationRayShape3D.new()
		ray.length = 0.5
		ray.slide_on_slope = false
		var rs := CollisionShape3D.new()
		rs.shape = ray
		rs.position = Vector3(0, 0.5, 0)
		rs.rotation = Vector3(deg_to_rad(90), 0, 0)
		add_child(rs)
	else:
		cap.height = 1.75
		body_shape.shape = cap
		body_shape.position = Vector3(0, 0.88, 0)
	add_child(body_shape)


func chest() -> Vector3:
	return global_position + Vector3.UP * 1.3


func facing() -> Vector3:
	var f := -global_transform.basis.z
	f.y = 0.0
	return f.normalized() if f.length() > 0.01 else Vector3.FORWARD


func muzzle() -> Vector3:
	if muzzle_node and is_instance_valid(muzzle_node):
		return muzzle_node.global_position
	return global_position + Vector3.UP * 1.35 + facing() * 0.45


func def() -> Dictionary:
	return Combat.defn(weapon)


func set_model(m: String) -> void:
	model = m
	if rig:
		rig.queue_free()
	rig = Rig.create(m, self)
	if tint != Color.WHITE and rig.root:
		for mi in G.game.models.meshes(rig.root):
			var mat: Material = mi.get_active_material(0)
			if mat is BaseMaterial3D:
				mat = mat.duplicate()
				mat.albedo_color = tint
				mi.material_override = mat
	if blob == null:
		blob = G.game.models.blob(self, 1.1, 1.1, 0.6)
	weapon_node = null
	equip(weapon, true)


func equip(w: int, force := false) -> void:
	if w == weapon and not force and (weapon_node != null or def()["model"] == ""):
		return
	weapon = w
	if weapon_node and is_instance_valid(weapon_node):
		weapon_node.queue_free()
	weapon_node = null
	muzzle_node = null
	var d := Combat.defn(w)
	if d["model"] == "" or rig == null or rig.skeleton == null:
		return
	var hand := rig.bone_attachment("Hand_R")
	if hand == null:
		return
	weapon_node = G.game.models.weapon(d["model"])
	if weapon_node == null:
		return
	hand.add_child(weapon_node)
	var dv := rig.hand_tip_r - rig.hand_r
	if dv.length_squared() < 1e-4:
		dv = Vector3.DOWN
	# the bone's rest frame is the model frame (rest rotations are identity): grip in the palm, barrel along the fingers
	weapon_node.transform = Transform3D(Basis.looking_at(dv.normalized(), Vector3(0, 0, -1)), dv * 0.45)
	var ws: Dictionary = G.game.models.weapons.get(d["model"], {})
	if not ws.is_empty() and not d["melee"]:
		muzzle_node = Node3D.new()
		weapon_node.add_child(muzzle_node)
		muzzle_node.position = ws["muzzle"]


func show_body(on: bool) -> void:
	if rig:
		rig.visible = on
	if blob:
		blob.visible = on and vehicle == null


func hurt(dmg: float, from: Vector3, by: Human, melee: bool) -> void:
	if dead:
		return
	if armor > 0.0:
		var a := minf(armor, dmg * 0.7)
		armor -= a
		dmg -= a
	health -= dmg
	if rig and vehicle == null:
		rig.play("hit", 0.05, 1.0, true)
	if health <= 0.0:
		die(by)


func die(by: Human) -> void:
	if dead:
		return
	dead = true
	health = 0.0
	dead_time = G.now
	if rig:
		rig.play("death", 0.1)
	G.audio.at("grunt" if randf() < 0.5 else "body_fall", chest(), 0.9, 1.0, 5.0)
	collision_layer = 0


func hit_by_vehicle(v: Vehicle, spd: float) -> void:
	if dead or vehicle != null or spd < 3.0:
		return
	hurt(spd * 7.0, v.global_position, v.driver, false)
	knocked = 1.6
	var push := global_position - v.global_position
	push.y = 0.0
	global_position += push.normalized() * 0.8
	G.audio.at("body_fall", chest(), 1.0, 1.0, 6.0)


## Turns the body smoothly to a direction.
func face_towards(dir: Vector3, deg_per_sec: float, delta: float) -> void:
	dir.y = 0.0
	if dir.length_squared() < 1e-4:
		return
	var want := atan2(-dir.x, -dir.z)
	var cur := rotation.y
	var diff := wrapf(want - cur, -PI, PI)
	var step := deg_to_rad(deg_per_sec) * delta
	rotation.y = cur + clampf(diff, -step, step)
