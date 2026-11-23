extends CharacterBody3D
## First-person player: walks with the on-screen joystick (or WASD), looks around by dragging
## the screen (or the mouse) and plays Unity's footstep sounds while walking.

const WALK_SPEED := 2.0          # metres per second (Granny-style slow walk)
const EYE_HEIGHT := 1.6
const STRIDE := 0.85             # metres walked between two footsteps
const LOOK_SPEED := 0.0022       # radians per screen pixel at sensitivity 1.0

## How fast the camera turns when you drag the screen.
@export var look_sensitivity := 1.0
## Footstep sounds; one is picked at random each step (never the same twice in a row).
@export var footstep_sounds: Array[AudioStream] = []

var move_input := Vector2.ZERO   # set by the on-screen joystick, x = right, y = back

var _pitch := 0.0
var _stride_left := 0.0
var _bob_time := 0.0
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var interact_ray: RayCast3D = $Head/Camera3D/InteractRay
@onready var footsteps: AudioStreamPlayer = $Footsteps


func _ready() -> void:
	interact_ray.add_exception(self)
	head.position.y = EYE_HEIGHT


func _physics_process(delta: float) -> void:
	# keyboard keys work too (for testing on a computer)
	var input := move_input
	var keys := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if keys != Vector2.ZERO:
		input = keys
	input = input.limit_length(1.0)

	var direction := transform.basis * Vector3(input.x, 0.0, input.y)
	velocity.x = move_toward(velocity.x, direction.x * WALK_SPEED, 12.0 * delta)
	velocity.z = move_toward(velocity.z, direction.z * WALK_SPEED, 12.0 * delta)
	if not is_on_floor():
		velocity.y -= _gravity * delta
	move_and_slide()
	_update_footsteps(delta)


func look(drag: Vector2) -> void:
	var amount := LOOK_SPEED * look_sensitivity
	rotate_y(-drag.x * amount)
	_pitch = clampf(_pitch - drag.y * amount, deg_to_rad(-85.0), deg_to_rad(85.0))
	head.rotation.x = _pitch


## The thing the player is looking at and can use (the door), or null.
func get_interactable() -> Node:
	if interact_ray.is_colliding():
		var target := interact_ray.get_collider()
		if target and target.has_method("interact"):
			return target
	return null


func interact() -> void:
	var target := get_interactable()
	if target:
		target.interact()


func _update_footsteps(delta: float) -> void:
	var ground_speed := Vector2(velocity.x, velocity.z).length()
	if not is_on_floor() or ground_speed < 0.3:
		_stride_left = 0.0
		camera.position.y = lerpf(camera.position.y, 0.0, 6.0 * delta)
		return

	# gentle head bob, a little like Granny
	_bob_time += delta * ground_speed * 3.6
	camera.position.y = sin(_bob_time) * 0.025

	_stride_left -= ground_speed * delta
	if _stride_left <= 0.0:
		_stride_left = STRIDE
		_play_footstep()


func _play_footstep() -> void:
	if footstep_sounds.size() < 2:
		return
	# Same trick as Unity's FirstPersonController: pick from all but the first sound,
	# play it, then swap it to the front so it can't play twice in a row.
	var n := randi_range(1, footstep_sounds.size() - 1)
	footsteps.stream = footstep_sounds[n]
	footsteps.pitch_scale = randf_range(0.95, 1.05)
	footsteps.play()
	footstep_sounds[n] = footstep_sounds[0]
	footstep_sounds[0] = footsteps.stream
