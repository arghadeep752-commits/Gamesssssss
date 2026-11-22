class_name Cam
extends Node3D
## Third-person camera: orbit by dragging, follows behind vehicles, slow orbit in the menu.

var cam: Camera3D
var yaw := 0.0                 # degrees, Godot (rotation about +Y)
var pitch := 12.0              # degrees, looking down is positive
var dist := 4.4
var look := Vector2.ZERO       # drag input this frame (pixels, y up)
var sensitivity := 1.0
var idle := 0.0
var _shake := 0.0
var cur_dist := 4.4
var focus := Vector3.ZERO
var menu_orbit := false
var orbit_centre := Vector3.ZERO


static func create(parent: Node) -> Cam:
	var c := Cam.new()
	c.name = "Cam"
	parent.add_child(c)
	c.cam = Camera3D.new()
	c.cam.near = 0.15
	c.cam.far = 1600.0
	c.cam.fov = 60.0
	c.add_child(c.cam)
	c.cam.current = true
	G.cam = c
	return c


func shake(s: float) -> void:
	_shake = maxf(_shake, s)


func forward() -> Vector3:
	return -cam.global_transform.basis.z


func flat() -> Vector3:
	var f := forward()
	f.y = 0.0
	return f.normalized() if f.length_squared() > 1e-4 else Vector3.FORWARD


func visible_point(p: Vector3) -> bool:
	return cam.is_position_in_frustum(p + Vector3.UP)


func _rot() -> Basis:
	return Basis.from_euler(Vector3(deg_to_rad(-pitch), deg_to_rad(yaw), 0.0), EULER_ORDER_YXZ)


func _process(delta: float) -> void:
	var dt := delta
	if menu_orbit:
		yaw += dt * 4.0
		var q := Basis.from_euler(Vector3(deg_to_rad(-14.0), deg_to_rad(yaw), 0.0), EULER_ORDER_YXZ)
		var pos := orbit_centre + q * Vector3(0, 0, 150) + Vector3.UP * 45.0
		cam.global_transform = Transform3D(Basis.looking_at(orbit_centre + Vector3.UP * 10.0 - pos, Vector3.UP), pos)
		return
	var p := Player.I
	if p == null:
		return
	var v := p.vehicle
	var target: Vector3
	var want_dist: float
	if v:
		target = v.global_position + Vector3.UP * (v.spec["height"] * 0.75 + 0.6)
		want_dist = v.spec["length"] * 0.85 + 3.4 + (6.0 if v.is_heli() else 0.0)
	else:
		target = p.global_position + Vector3.UP * 1.55
		want_dist = dist * (0.8 if p.fire and not p.def()["melee"] else 1.0)
	if look.length_squared() > 0.01:
		yaw -= look.x * 0.18 * sensitivity
		pitch = clampf(pitch - look.y * 0.14 * sensitivity, -25.0, 70.0)
		idle = 0.0
	else:
		idle += dt
	look = Vector2.ZERO
	if v and idle > 1.2 and v.speed() > 3.0:
		# swing back behind the vehicle
		var f: Vector3 = v.forward() if v.forward_speed() >= 0.0 else -v.forward()
		var vy := rad_to_deg(atan2(-f.x, -f.z))
		yaw = rad_to_deg(lerp_angle(deg_to_rad(yaw), deg_to_rad(vy), minf(1.0, dt * 2.2)))
		pitch = lerpf(pitch, 18.0 if v.is_heli() else 9.0, minf(1.0, dt * 1.5))
	focus = focus.lerp(target, 1.0 - exp(-dt * (14.0 if v else 20.0)))
	if focus.distance_squared_to(target) > 100.0:
		focus = target
	var rot := _rot()
	var back := rot.z                # the camera's back is +Z
	var d := want_dist
	var space := get_world_3d().direct_space_state
	var q := PhysicsShapeQueryParameters3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.25
	q.shape = sph
	q.transform = Transform3D(Basis(), focus)
	q.motion = back * want_dist
	q.collision_mask = G.L_WORLD
	var res := space.cast_motion(q)
	if res.size() == 2 and res[0] < 1.0:
		d = maxf(0.8, res[0] * want_dist - 0.1)
	cur_dist = d if d < cur_dist else lerpf(cur_dist, d, minf(1.0, dt * 3.0))
	var pos := focus + back * cur_dist
	if _shake > 0.0:
		pos += Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * _shake * 0.25
		_shake = maxf(0.0, _shake - dt * 2.5)
	cam.global_transform = Transform3D(rot, pos)
	var fov := 60.0 + (clampf(v.speed() / 40.0, 0.0, 1.0) * 10.0 if v else 0.0)
	cam.fov = lerpf(cam.fov, fov, minf(1.0, dt * 3.0))
