extends CharacterBody3D
## Fast first-person player (no crouch / stand).
## Phone: joystick + swipe to look (handled by the HUD).
## PC: WASD / arrows, drag the mouse to look, E to use.

const InteractScript = preload("res://scripts/interactable.gd")

const SPEED := 6.2
const ACCEL := 42.0
const GRAVITY := 20.0
const STEP_DISTANCE := 1.9
const EYE_HEIGHT := 1.55
const USE_DISTANCE := 2.6

var game
var head: Node3D
var cam: Camera3D
var yaw := 0.0
var pitch := 0.0
var move_input := Vector2.ZERO
var controls_enabled := true

var _step_accum := 0.0
var _bob := 0.0
var _step_player: AudioStreamPlayer


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.6
	floor_max_angle = deg_to_rad(50.0)
	floor_constant_speed = true
	var shape := CapsuleShape3D.new()
	shape.radius = 0.3
	shape.height = 1.7
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position = Vector3(0, 0.85, 0)
	add_child(cs)

	head = Node3D.new()
	head.name = "Head"
	head.position = Vector3(0, EYE_HEIGHT, 0)
	add_child(head)
	cam = Camera3D.new()
	cam.name = "Camera"
	cam.fov = 72.0
	cam.near = 0.05
	cam.far = 90.0
	head.add_child(cam)
	cam.current = true

	_step_player = AudioStreamPlayer.new()
	_step_player.volume_db = -5.0
	add_child(_step_player)


func set_look(new_yaw: float, new_pitch: float) -> void:
	yaw = new_yaw
	pitch = clampf(new_pitch, deg_to_rad(-80.0), deg_to_rad(80.0))
	rotation.y = yaw
	if head != null:
		head.rotation.x = pitch


## Called by the HUD with the finger movement in pixels.
func look(relative: Vector2) -> void:
	if not controls_enabled:
		return
	var s: float = Global.sensitivity * 0.2
	set_look(yaw - deg_to_rad(relative.x * s), pitch - deg_to_rad(relative.y * s))


func _physics_process(delta: float) -> void:
	var input := move_input
	var kb := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		kb.y += 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		kb.y -= 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		kb.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		kb.x += 1.0
	if kb != Vector2.ZERO:
		input = kb.normalized()
	if not controls_enabled:
		input = Vector2.ZERO

	var amount := minf(input.length(), 1.0)
	var dir := Vector3.ZERO
	if amount > 0.08:
		dir = (global_transform.basis * Vector3(input.x, 0.0, -input.y))
		dir.y = 0.0
		dir = dir.normalized()
	var target := dir * SPEED * amount
	velocity.x = move_toward(velocity.x, target.x, ACCEL * delta)
	velocity.z = move_toward(velocity.z, target.z, ACCEL * delta)
	if is_on_floor():
		velocity.y = -0.5
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	_footsteps(delta)


func _footsteps(delta: float) -> void:
	var hspeed := Vector2(velocity.x, velocity.z).length()
	if is_on_floor() and hspeed > 0.6:
		_step_accum += hspeed * delta
		_bob += hspeed * delta * 2.4
		if _step_accum >= STEP_DISTANCE:
			_step_accum = 0.0
			var s := Assets.get_sound("step_wood")
			if s != null:
				_step_player.stream = s
				_step_player.pitch_scale = randf_range(0.92, 1.08)
				_step_player.play()
			if game != null:
				game.on_player_step()
	var amount := clampf(hspeed / SPEED, 0.0, 1.0)
	head.position.y = EYE_HEIGHT + sin(_bob) * 0.035 * amount


## The interactable object the player is looking at (or null).
func get_focus():
	var from := cam.global_position
	var to := from - cam.global_transform.basis.z * USE_DISTANCE
	var q := PhysicsRayQueryParameters3D.create(from, to, 1 | 8)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return null
	var c = hit.get("collider")
	if c != null and c is InteractScript:
		return c
	return null
