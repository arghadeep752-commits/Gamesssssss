class_name Player
extends CharacterBody3D
## The first-person player, made for a touch screen.
## - Turning and walking are updated every rendered frame, so they stay smooth whatever the frame rate
##   (moving only on physics ticks made the view judder on phones that render slower than 60 fps).
## - Walking speeds up and stops within a fraction of a second, without the old sliding.
## - The view follows the thumb, smoothed over a few hundredths of a second so touch jitter disappears;
##   the turn per finger movement is the same on every screen size.
## - The view bobs gently while walking, with a footstep at the bottom of every bob.
## - Standing up is refused where there is no room above you.

var cam: Camera3D
var hud: Hud
var yaw := 0.0
var pitch := 0.0
var sensitivity := 1.0
var crouched := false
var hidden := false
var frozen := false
var eye := 1.6
var audio = null
var bob := 0.0
var _look_left := Vector2.ZERO      # drag not yet turned into rotation
var _bob_amp := 0.0
var _bob_low := false
const WALK := 3.3
const CROUCH := 1.7
const ACCEL := 15.0                 # m/s² speeding up
const DECEL := 24.0                 # m/s² slowing down or changing direction
const LOOK := 0.0042                # radians per pixel of drag on a 720-pixel-high screen
const STAND_H := 1.7
const CROUCH_H := 1.0


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.3
	floor_constant_speed = true
	safe_margin = 0.01
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.28
	cap.height = STAND_H
	cs.shape = cap
	cs.position.y = STAND_H / 2
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
	if crouched and not c and test_move(global_transform, Vector3(0, STAND_H - CROUCH_H + 0.05, 0)):
		if hud:
			hud.show_message("No room to stand up", 1.5)
		return
	crouched = c
	var cs: CollisionShape3D = $Shape
	(cs.shape as CapsuleShape3D).height = CROUCH_H if c else STAND_H
	cs.position.y = (CROUCH_H if c else STAND_H) / 2


func face(target: Vector3) -> void:
	var d := target - global_position
	yaw = atan2(-d.x, -d.z)
	pitch = 0.0
	_look_left = Vector2.ZERO


func _process(dt: float) -> void:
	dt = minf(dt, 0.1)                  # a long hitch must not throw the player through a wall
	_turn(dt)
	eye = lerpf(eye, 0.85 if crouched else 1.6, 1.0 - exp(-dt * 10.0))
	if frozen or hidden or hud == null:
		velocity = Vector3.ZERO
		_bob_amp = 0.0
		cam.position.y = eye
		return
	_walk(dt)
	_bob(dt)


func _turn(dt: float) -> void:
	if hud:
		if not frozen:
			_look_left += hud.look
		hud.look = Vector2.ZERO
	if frozen:
		_look_left = Vector2.ZERO
	var take := _look_left * (1.0 - exp(-dt * 26.0))
	_look_left -= take
	var k := LOOK * sensitivity * 720.0 / maxf(get_viewport().get_visible_rect().size.y, 1.0)
	yaw -= take.x * k
	pitch = clampf(pitch - take.y * k, -1.35, 1.35)
	rotation.y = yaw
	cam.rotation.x = pitch


func _walk(dt: float) -> void:
	var m := hud.move
	if m.length() > 1.0:
		m = m.normalized()
	var want := global_transform.basis * Vector3(m.x, 0.0, m.y) * (CROUCH if crouched else WALK)
	want.y = 0.0
	var cur := Vector3(velocity.x, 0.0, velocity.z)
	var speeding_up := want.length() > cur.length() and (cur.length() < 0.2 or want.normalized().dot(cur.normalized()) > 0.8)
	cur = cur.move_toward(want, (ACCEL if speeding_up else DECEL) * dt)
	velocity.x = cur.x
	velocity.z = cur.z
	velocity.y = -0.5 if is_on_floor() else maxf(velocity.y - 20.0 * dt, -25.0)
	move_and_slide()


func _bob(dt: float) -> void:
	var hv := Vector2(velocity.x, velocity.z).length()
	_bob_amp = lerpf(_bob_amp, clampf(hv / WALK, 0.0, 1.0), 1.0 - exp(-dt * 8.0))
	if hv > 0.3:
		bob += dt * (5.0 + hv * 2.4) * (0.8 if crouched else 1.0)
	var s := sin(bob)
	# a footstep every time the head reaches the bottom of the bob
	if s < -0.9 and not _bob_low and hv > 0.6:
		_bob_low = true
		if audio:
			audio.play("footstep_%d" % randi_range(1, 6), -16.0 if crouched else -9.0, randf_range(0.92, 1.08))
	elif s > 0.0:
		_bob_low = false
	cam.position.y = eye + s * 0.026 * _bob_amp
	cam.position.x = cos(bob * 0.5) * 0.012 * _bob_amp
