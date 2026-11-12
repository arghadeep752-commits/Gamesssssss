class_name CameraRig
extends Camera2D
## Smooth follow camera with look-ahead, level limits and trauma-based screen shake.

var target: Node2D
var look_ahead := 150.0
var vertical_bias := -140.0
var _look := 0.0
var _shake := 0.0
var _shake_time := 0.0
var _focus_override: Variant = null
var _noise_t := 0.0


func _ready() -> void:
	zoom = Vector2(0.9, 0.9)
	position_smoothing_enabled = false
	process_callback = Camera2D.CAMERA2D_PROCESS_PHYSICS
	Events.camera_shake.connect(shake)


func setup_limits(size: Vector2) -> void:
	limit_left = 0
	limit_top = -200
	limit_right = int(size.x)
	limit_bottom = int(size.y)


func set_arena_limits(left: float, right: float) -> void:
	limit_left = int(left - 40)
	limit_right = int(right + 40)


func shake(strength: float, duration: float) -> void:
	if int(SaveManager.setting("quality")) == 0:
		strength *= 0.5
	_shake = max(_shake, strength)
	_shake_time = max(_shake_time, duration)


func focus_on(pos: Variant) -> void:
	_focus_override = pos


func snap() -> void:
	if target:
		global_position = target.global_position + Vector2(0, vertical_bias)
	reset_smoothing()


func _physics_process(delta: float) -> void:
	if target == null or not is_instance_valid(target):
		return
	var desired: Vector2
	if _focus_override != null:
		desired = _focus_override
	else:
		var vx := 0.0
		if target is CharacterBody2D:
			vx = (target as CharacterBody2D).velocity.x
		var want := clampf(vx / 340.0, -1.0, 1.0) * look_ahead
		_look = lerpf(_look, want, 1.0 - exp(-2.5 * delta))
		desired = target.global_position + Vector2(_look, vertical_bias)
	global_position = global_position.lerp(desired, 1.0 - exp(-7.0 * delta))
	if _shake_time > 0.0:
		_shake_time -= delta
		_noise_t += delta * 40.0
		var k: float = _shake * (_shake_time / maxf(0.01, _shake_time + 0.15))
		offset = Vector2(sin(_noise_t * 1.7) * k, cos(_noise_t * 2.3) * k)
	else:
		offset = offset.lerp(Vector2.ZERO, 0.3)
		_shake = 0.0
