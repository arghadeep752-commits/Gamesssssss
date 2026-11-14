class_name Player
extends CharacterBody3D

var cam: Camera3D
var hud: Hud
var yaw := 0.0
var pitch := 0.0
var sensitivity := 1.0
var crouched := false
var hidden := false
var frozen := false
var eye := 1.6
var step_acc := 0.0
var audio = null
var bob := 0.0
const WALK := 3.3
const CROUCH := 1.7


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.28
	cap.height = 1.7
	cs.shape = cap
	cs.position.y = 0.85
	cs.name = "Shape"
	add_child(cs)
	cam = Camera3D.new()
	cam.fov = 68
	cam.near = 0.05
	cam.far = 120
	cam.position.y = eye
	add_child(cam)
	var hold := Node3D.new()
	hold.name = "Hold"
	hold.position = Vector3(0.3, -0.24, -0.55)
	cam.add_child(hold)


func head() -> Vector3:
	return cam.global_position


func forward() -> Vector3:
	return -cam.global_transform.basis.z


func set_crouch(c: bool) -> void:
	crouched = c
	var cs: CollisionShape3D = $Shape
	(cs.shape as CapsuleShape3D).height = 1.0 if c else 1.7
	cs.position.y = 0.5 if c else 0.85


func face(target: Vector3) -> void:
	var d := target - global_position
	yaw = atan2(-d.x, -d.z)
	pitch = 0.0


func _physics_process(dt: float) -> void:
	if hud and not frozen:
		yaw -= hud.look.x * 0.0042 * sensitivity
		pitch = clampf(pitch - hud.look.y * 0.0042 * sensitivity, -1.35, 1.35)
		hud.look = Vector2.ZERO
	rotation.y = yaw
	cam.rotation.x = pitch
	var target_eye := 0.85 if crouched else 1.6
	eye = lerpf(eye, target_eye, clampf(dt * 9.0, 0, 1))
	if frozen or hidden or hud == null:
		velocity = Vector3.ZERO
		cam.position.y = eye
		return
	var m := hud.move
	var dir := (transform.basis * Vector3(m.x, 0, m.y))
	var sp := CROUCH if crouched else WALK
	velocity.x = dir.x * sp
	velocity.z = dir.z * sp
	velocity.y = -4.0 if not is_on_floor() else 0.0
	move_and_slide()
	var hv := Vector2(velocity.x, velocity.z).length()
	if hv > 0.4:
		bob += dt * hv * 2.1
		step_acc += dt * hv
		if step_acc > (1.25 if crouched else 1.9):
			step_acc = 0.0
			if audio:
				audio.play("footstep_%d" % randi_range(1, 6), -16.0 if crouched else -9.0, randf_range(0.92, 1.08))
	cam.position.y = eye + sin(bob * 2.0) * 0.028 * clampf(hv / WALK, 0, 1)
