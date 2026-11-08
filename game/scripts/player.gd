extends CharacterBody3D
## First person player: joystick walks, run button runs, dragging looks around. A flashlight is always on.

signal stepped(loudness: float)

const WALK_SPEED := 2.05
const RUN_SPEED := 3.7
const EYE_HEIGHT := 1.58

var hud
var frozen := false
var yaw := 0.0
var pitch := 0.0
var head: Node3D
var camera: Camera3D
var flashlight: SpotLight3D
var noise := 0.0                 # 0 = silent, 1 = running
var running := false
var _bob := 0.0
var _step_acc := 0.0
var _shake := 0.0
var _flicker := 0.0
var _vel_h := Vector3.ZERO

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	col.shape = cap
	col.position.y = 0.85
	add_child(col)
	head = Node3D.new()
	head.position.y = EYE_HEIGHT
	add_child(head)
	camera = Camera3D.new()
	camera.fov = 66.0
	camera.near = 0.05
	camera.far = 70.0
	camera.current = true
	head.add_child(camera)
	flashlight = SpotLight3D.new()
	flashlight.light_color = Color(1.0, 0.93, 0.8)
	flashlight.light_energy = 3.2
	flashlight.spot_range = 17.0
	flashlight.spot_angle = 34.0
	flashlight.spot_angle_attenuation = 0.7
	flashlight.spot_attenuation = 0.8
	flashlight.shadow_enabled = true
	flashlight.shadow_bias = 0.04
	flashlight.shadow_normal_bias = 1.0
	camera.add_child(flashlight)

func look_delta(d: Vector2) -> void:
	if frozen:
		return
	var k := 0.085 * Settings.sensitivity
	yaw -= d.x * k
	pitch = clampf(pitch - d.y * k, -78.0, 78.0)

func face(yaw_deg: float, pitch_deg: float) -> void:
	yaw = yaw_deg
	pitch = pitch_deg

func add_shake(v: float) -> void:
	_shake = maxf(_shake, v)

func flicker_light(t: float) -> void:
	_flicker = maxf(_flicker, t)

func _physics_process(dt: float) -> void:
	rotation_degrees.y = yaw
	head.rotation_degrees.x = pitch
	var mv := Vector2.ZERO
	var want_run := false
	if hud and not frozen:
		mv = hud.move_vec
		want_run = hud.run_held
	running = want_run and mv.length() > 0.25
	var speed := RUN_SPEED if running else WALK_SPEED
	var dir := (global_transform.basis * Vector3(mv.x, 0.0, mv.y))
	dir.y = 0.0
	var target := dir * speed * minf(1.0, mv.length() * 1.15)
	_vel_h = _vel_h.lerp(target, clampf(dt * 9.0, 0.0, 1.0))
	velocity.x = _vel_h.x
	velocity.z = _vel_h.z
	velocity.y = 0.0 if is_on_floor() else velocity.y - 18.0 * dt
	move_and_slide()
	var moved := Vector2(velocity.x, velocity.z).length()
	noise = 0.0
	if moved > 0.4:
		noise = 1.0 if running else 0.4
		_bob += dt * moved * (3.6 if running else 3.2)
		_step_acc += moved * dt
		var stride := 1.2 if running else 1.55
		if _step_acc >= stride:
			_step_acc = 0.0
			Sfx.play("footstep", -6.0 if running else -10.0, randf_range(0.92, 1.08))
			stepped.emit(noise)
	var bob_amp := 0.045 if running else 0.026
	var sh := _shake * 0.025
	head.position = Vector3(sin(_bob * 0.5) * bob_amp * 0.6 + randf_range(-sh, sh), EYE_HEIGHT + absf(sin(_bob)) * bob_amp + randf_range(-sh, sh), 0.0)
	camera.rotation.z = sin(_bob * 0.5) * 0.008 * (2.0 if running else 1.0) + randf_range(-sh, sh) * 0.6
	_shake = maxf(0.0, _shake - dt * 1.5)
	if _flicker > 0.0:
		_flicker -= dt
		flashlight.light_energy = 3.2 * (0.15 + 0.85 * float(randf() > 0.45))
	else:
		flashlight.light_energy = lerpf(flashlight.light_energy, 3.2, clampf(dt * 8.0, 0.0, 1.0))
