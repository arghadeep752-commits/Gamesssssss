class_name Vehicle
extends RigidBody3D
## Every vehicle: cars, autos, bikes and scooters on ray-cast wheels with springs and tyre grip, the helicopter,
## the speedboat on the water. Traffic drives them kinematically along the lanes; anyone can pull the driver out.

static var all: Array = []

var spec: Dictionary
var driver: Human = null
var npc_driver := false
var traffic := false
var wrecked := false
var owned := false
var siren := false
var parked := false
var health := 1000.0
var burning := 0.0
var steer := 0.0
var throttle := 0.0
var brake := 0.0
var lift := 0.0
var handbrake := false
var kin_speed := 0.0
var paint := Color.WHITE
var body: Node3D
var last_x: PackedFloat32Array = []
var rotor := 0.0
var flip_timer := 0.0
var next_crash := 0.0
var engine_vol := 0.0
var engine: AudioStreamPlayer3D
var rotor_disc: MeshInstance3D
var lights: MeshInstance3D
var siren_node: MeshInstance3D
var grounded := false
var frozen_wait := false
var tcar = null               # traffic driving state (Traffic.TrafficCar)
var ai = null                 # police driver (AIDriver)
var _prev_v := Vector3.ZERO
var _glow_mat: ShaderMaterial
var _glow_mat_always: ShaderMaterial


func _enter_tree() -> void:
	if not all.has(self):
		all.append(self)


func _exit_tree() -> void:
	all.erase(self)


func is_bike() -> bool:
	return spec["cls"] == "bike"


func is_heli() -> bool:
	return spec["cls"] == "heli"


func is_boat() -> bool:
	return spec["cls"] == "boat"


func speed() -> float:
	return kin_speed if freeze else linear_velocity.length()


func forward() -> Vector3:
	return -global_transform.basis.z


func forward_speed() -> float:
	return kin_speed if freeze else linear_velocity.dot(forward())


func seat_pos() -> Vector3:
	var s: Vector3 = spec["seat"]
	return s + (Vector3(0, -0.52, 0) if spec["open"] else Vector3(0, -0.45, 0))


static func spawn(parent: Node, m: String, pos: Vector3, yaw: float, traffic_mode: bool, col: Color) -> Vehicle:
	var models = G.game.models
	if not models.vehicles.has(m):
		push_warning("no vehicle " + m)
		return null
	var s: Dictionary = models.vehicles[m]
	var v := Vehicle.new()
	v.name = "veh_" + m
	v.spec = s
	v.paint = col
	v.traffic = traffic_mode
	v.collision_layer = G.L_VEHICLE
	v.collision_mask = G.L_WORLD | G.L_VEHICLE
	v.body = models.vehicle(m, col)
	if v.body:
		v.add_child(v.body)
	var H: float = s["height"]
	var W: float = s["width"]
	var Lg: float = s["length"]
	var box := BoxShape3D.new()
	var cs := CollisionShape3D.new()
	if s["cls"] == "heli":
		box.size = Vector3(W * 0.32, H * 0.62, Lg * 0.62)
		cs.position = Vector3(0, H * 0.33, -Lg * 0.1)
	elif s["cls"] == "boat":
		box.size = Vector3(W * 0.9, H * 0.55, Lg * 0.92)
		cs.position = Vector3(0, H * 0.3, 0)
	else:
		var bike: bool = s["cls"] == "bike"
		var bottom := 0.3 if bike else maxf(0.28, H * 0.22)
		var top := H * (0.85 if bike else 0.92)
		box.size = Vector3(W * 0.5 if bike else W * 0.94, top - bottom, Lg * 0.95)
		cs.position = Vector3(0, (top + bottom) * 0.5, 0)
	cs.shape = box
	v.add_child(cs)
	v.mass = s["mass"]
	v.linear_damp = 0.03
	v.angular_damp = 2.5 if s["cls"] == "heli" else 1.5
	v.center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	var com_y := 0.35 if s["cls"] == "bike" else (H * 0.35 if s["cls"] == "heli" else (H * 0.15 if s["cls"] == "boat" else H * 0.2))
	v.center_of_mass = Vector3(0, com_y, 0)
	v.continuous_cd = true
	v.can_sleep = false
	v.custom_integrator = false
	v.freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
	v.freeze = traffic_mode
	v.last_x.resize(maxi(1, s["wheels"].size()))
	parent.add_child(v)
	v.global_transform = Transform3D(Basis(Vector3.UP, deg_to_rad(yaw)), pos)
	if not traffic_mode:
		v.brake = 1.0
		v.handbrake = true
		v.parked = true
	if s["cls"] != "heli" and s["cls"] != "boat":
		models.blob(v, W * 1.15, Lg * 1.08, 0.7)
	elif s["cls"] == "heli":
		models.blob(v, W * 0.6, Lg * 0.8, 0.6)
	if s["cls"] == "heli" and s.get("rotor_r", 0.0) > 0.0:
		v.make_rotor()
	v.make_lights()
	return v


# ------------------------------------------------------------------ drivers
func take_driver(h: Human) -> void:
	driver = h
	npc_driver = false
	parked = false
	if tcar:
		G.traffic.detach(tcar)
	if freeze:
		freeze = false
		linear_velocity = forward() * kin_speed
	traffic = false
	handbrake = false


func release_driver() -> void:
	driver = null
	steer = 0.0
	throttle = 0.0
	lift = 0.0
	brake = 1.0
	handbrake = true


## Puts the driver out on the street (car-jacking, crashes, death).
func eject() -> void:
	var ex: Vector3 = global_transform * spec["exit"]
	ex.y = G.city.ground(ex, global_position.y)
	var d := driver
	if d is Ped:
		var p: Ped = d
		p.get_parent().remove_child(p)
		G.game.world.add_child(p)
		p.global_position = ex
		p.rotation = Vector3(0, rotation.y, 0)
		p.show_body(true)
		p.vehicle = null
		p.collision_layer = G.L_PED
		p.st = Ped.IDLE
		if not p.dead:
			p.flee(global_position, 10.0)
	elif npc_driver:
		var names := ["npc_man", "npc_student", "npc_oldman"]
		var p := Ped.create(G.game.world, names[randi() % names.size()], ex, rad_to_deg(rotation.y) + 90.0, false)
		p.path = -1
		Traffic.adopt(p)
		p.flee(global_position, 10.0)
	if not (d is Player):
		driver = null
	npc_driver = false
	release_driver()
	if tcar:
		G.traffic.detach(tcar)
	if freeze:
		freeze = false
		linear_velocity = forward() * kin_speed
	traffic = false


# ------------------------------------------------------------------ physics
func accel() -> float:
	match spec["name"]:
		"sports_car":
			return 8.5
		"bus", "truck":
			return 2.4
		"auto_rickshaw":
			return 2.8
		"e_rickshaw":
			return 2.0
		"motorbike":
			return 6.5
		"scooter":
			return 4.2
	return 4.8


func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	if freeze:
		return
	var dt := state.step
	if wrecked:
		throttle = 0.0
		steer = 0.0
		lift = 0.0
	if is_heli():
		heli(state, dt)
	elif is_boat():
		boat(state, dt)
	else:
		wheels(state, dt)
	crash_check(state)


## Arcade driving: spring suspension on ray-cast wheels for the bumps, but speed, steering and grip are set
## directly, and the body is kept upright on the ground (bikes lean into turns), so nothing flips or spins out.
func wheels(state: PhysicsDirectBodyState3D, dt: float) -> void:
	var ws: Array = spec["wheels"]
	var n := ws.size()
	if n == 0:
		return
	var xf := state.transform
	var up := xf.basis.y
	const TRAVEL := 0.24
	var m: float = spec["mass"]
	var share := m / n
	var k := share * 9.81 / (TRAVEL * 0.5)
	var c := 2.0 * sqrt(k * share) * 0.7
	var gcount := 0
	var nrm := Vector3.ZERO
	var space := state.get_space_state()
	for i in n:
		var w: Dictionary = ws[i]
		var r: float = w["r"]
		var length := TRAVEL + r
		var wp: Vector3 = w["pos"]
		var origin := xf * Vector3(wp.x, r + TRAVEL * 0.5, wp.z)
		var q := PhysicsRayQueryParameters3D.create(origin, origin - up * length, G.L_WORLD)
		var hit := space.intersect_ray(q)
		if hit.is_empty():
			last_x[i] = 0.0
			continue
		gcount += 1
		nrm += hit["normal"]
		var x: float = length - origin.distance_to(hit["position"])
		var fs := clampf(k * x + c * (x - last_x[i]) / dt, 0.0, share * 9.81 * 4.0)
		last_x[i] = x
		state.apply_force(up * fs, origin - xf.origin)
	grounded = gcount > 0
	var v := state.linear_velocity
	var top: float = spec["top"] / 3.6
	var bike := is_bike()
	if gcount * 2 >= n:
		nrm = nrm.normalized()
		var fwd := (-xf.basis.z).slide(nrm).normalized()
		var right := fwd.cross(nrm)
		var vf := v.dot(fwd)
		var vr := v.dot(right)
		var acc := 0.0
		if throttle > 0.01:
			acc = throttle * accel() * clampf(1.15 - maxf(0.0, vf) / top, 0.0, 1.0)
		elif throttle < -0.01:
			acc = (-10.0 * -throttle) if vf > 1.0 else (throttle * accel() * 0.6 if vf > -top * 0.25 else 0.0)
		if brake > 0.01:
			acc = -signf(vf) * minf(absf(vf) / dt, 11.0 * brake)
		if absf(throttle) < 0.01 and brake < 0.01:
			acc = -signf(vf) * minf(absf(vf) / dt, 1.4)      # rolling to a stop
		state.apply_central_force(fwd * acc * m)
		# tyre grip: remove most of the sideways slide (less with the handbrake: drifting)
		var grip := 2.2 if handbrake else (14.0 if bike else 9.0)
		state.apply_central_force(-right * vr * minf(grip, 1.0 / dt) * m)
		# steering sets the turn rate (right = clockwise from above = negative about +Y)
		var speed_f := clampf(absf(vf) / 3.0, 0.0, 1.0)
		var turn := steer * lerpf(2.3 if bike else 1.9, 0.9 if bike else 0.75, clampf(absf(vf) / top, 0.0, 1.0)) * speed_f * (1.0 if vf >= 0.0 else -1.0)
		if handbrake:
			turn *= 1.35
		# keep the body on the ground's slope; bikes lean into the turn
		var lean := (steer * clampf(absf(vf) / 10.0, 0.0, 1.0) * 24.0) if bike else 0.0
		var want_up := nrm.rotated(fwd, deg_to_rad(lean))
		var axis := up.cross(want_up)
		var ang := asin(clampf(axis.length(), 0.0, 1.0))
		if axis.length() > 1e-5:
			var fix := Basis(axis.normalized(), ang * clampf(dt * 8.0, 0.0, 1.0))
			state.transform = Transform3D(fix * xf.basis, xf.origin)
		var yaw_rate := lerpf(state.angular_velocity.dot(nrm), -turn, clampf(dt * 10.0, 0.0, 1.0))
		state.angular_velocity = nrm * yaw_rate
		# a little downforce keeps fast cars glued to the road
		state.apply_central_force(-nrm * absf(vf) * 0.15 * m)
	else:
		# in the air: level out slowly, no steering
		var axis := up.cross(Vector3.UP)
		var alpha := axis * 4.0 - state.angular_velocity * 1.2
		state.apply_torque(alpha / maxf(1e-6, state.inverse_inertia.length() / 1.732))
	if state.linear_velocity.length() > top * 1.15:
		state.linear_velocity = state.linear_velocity.normalized() * top * 1.15
	# upside down and stopped: put it back on its wheels
	if up.dot(Vector3.UP) < 0.35 and state.linear_velocity.length() < 2.0:
		flip_timer += dt
	else:
		flip_timer = 0.0
	if flip_timer > 1.5 and not wrecked:
		flip_timer = 0.0
		state.transform = Transform3D(Basis(Vector3.UP, rotation.y), xf.origin + Vector3.UP * 1.2)
		state.angular_velocity = Vector3.ZERO


func heli(state: PhysicsDirectBodyState3D, dt: float) -> void:
	var on := driver != null and not wrecked
	rotor = move_toward(rotor, 1.0 if on else 0.0, dt * (0.5 if on else 0.15))
	var m: float = spec["mass"]
	if rotor < 0.55:
		return
	var f := inverse_lerp(0.55, 1.0, rotor)
	var v := state.linear_velocity
	var vy := lift * 9.0
	state.apply_central_force(Vector3.UP * ((vy - v.y) * 2.2 + 9.81 * f) * m)
	var flat := G.flat(-state.transform.basis.z).normalized()
	var target_h := flat * (throttle * 52.0)
	var hv := G.flat(v)
	state.apply_central_force((target_h - hv) * 0.8 * f * m)
	var yaw := rotation.y - steer * deg_to_rad(75.0) * dt
	var want := Basis.from_euler(Vector3(-throttle * deg_to_rad(13.0), yaw, -steer * deg_to_rad(16.0)), EULER_ORDER_YXZ)
	var cur := state.transform.basis.orthonormalized()
	state.transform = Transform3D(Basis(cur.get_rotation_quaternion().slerp(want.get_rotation_quaternion(), clampf(dt * 2.5, 0.0, 1.0))), state.transform.origin)
	state.angular_velocity = Vector3.ZERO
	var q := PhysicsRayQueryParameters3D.create(state.transform.origin + Vector3.UP * 0.5, state.transform.origin + Vector3.DOWN * 0.5, G.L_WORLD)
	grounded = not state.get_space_state().intersect_ray(q).is_empty()


func boat(state: PhysicsDirectBodyState3D, _dt: float) -> void:
	var W: float = spec["width"] * 0.36
	var Lg: float = spec["length"] * 0.36
	var m: float = spec["mass"]
	var share := m / 4.0
	var k := share * 9.81 / maxf(0.15, spec.get("waterline", 0.5))
	var wet := 0
	var t := G.now
	var xf := state.transform
	for i in 4:
		var local := Vector3(-W if (i & 1) == 0 else W, 0.05, -Lg if (i & 2) == 0 else Lg)
		var p := xf * local
		var wl: float = G.city.water_level(p.x, p.z)
		if is_nan(wl):
			continue
		wl += sin(p.x * 0.05 + t * 0.9) * 0.18 + sin(p.z * 0.07 + t * 1.3) * 0.12
		var depth := wl - p.y
		if depth <= 0.0:
			continue
		wet += 1
		var vp := state.linear_velocity + state.angular_velocity.cross(p - xf.origin)
		state.apply_force(Vector3.UP * (minf(depth, 1.2) * k - vp.y * share * 1.6), p - xf.origin)
	grounded = wet > 0
	var v := state.linear_velocity
	if wet > 0:
		var f := -xf.basis.z
		var r := xf.basis.x
		var vl := v.dot(f)
		var vs := v.dot(r)
		var top: float = spec["top"] / 3.6
		var thrust := (throttle * 6.5 * (1.0 - clampf(vl / top, 0.0, 1.0)) if throttle > 0.0 else throttle * 3.0) * (1.0 if driver else 0.0)
		state.apply_central_force((f * (thrust - vl * 0.12) + r * (-vs * 1.8)) * m)
		state.apply_torque(Vector3.UP * -steer * clampf(vl / 4.0, -1.0, 1.0) * 1.6 / maxf(1e-6, state.inverse_inertia.y))
		angular_damp = 2.5
		linear_damp = 0.15
	else:
		linear_damp = 1.5
		angular_damp = 2.0


## A sudden change of speed is a crash (the physics engine has already stopped the vehicle).
func crash_check(state: PhysicsDirectBodyState3D) -> void:
	var v := state.linear_velocity
	var dv := (_prev_v - v).length()
	_prev_v = v
	if dv < 5.0 or state.get_contact_count() == 0:
		return
	for i in state.get_contact_count():
		var o = state.get_contact_collider_object(i)
		if o is Vehicle and o.freeze and o.tcar:
			o.call_deferred("traffic_crash", v)
	if G.now > next_crash:
		next_crash = G.now + 0.4
		G.audio.call_deferred("at", "crash" if dv > 14.0 else "glass_break", global_position, clampf(dv / 20.0, 0.0, 1.0), 1.0, 6.0)
		if driver and driver.is_player and G.cam:
			G.cam.shake(clampf(dv / 25.0, 0.0, 1.0))
	call_deferred("damage", (dv - 5.0) * (6.0 if is_bike() else 12.0), null)
	if is_bike() and dv > 18.0 and driver and driver.is_player:
		call_deferred("_throw_rider", dv)


func _throw_rider(dv: float) -> void:
	var p: Player = driver as Player
	if p == null:
		return
	p.exit_vehicle(true)
	p.hurt(dv * 1.5, global_position, null, false)
	p.knocked = 1.5


func traffic_crash(hit: Vector3) -> void:
	if tcar:
		G.traffic.crash(tcar, hit)


func damage(d: float, by: Human) -> void:
	if wrecked or d <= 0.0:
		return
	health -= d
	if by and by.is_player and spec["police"]:
		Wanted.crime(0.4, global_position, true)
	if health <= 0.0:
		wreck(by)


func wreck(by: Human) -> void:
	wrecked = true
	health = 0.0
	burning = 0.01
	if body:
		var dark := StandardMaterial3D.new()
		dark.albedo_color = Color(0.12, 0.1, 0.09)
		dark.roughness = 1.0
		for mi in G.game.models.meshes(body):
			mi.material_override = dark
	if by and by.is_player:
		Wanted.crime(1.5 if spec["police"] else 0.4, global_position, spec["police"])


# ------------------------------------------------------------------ visuals and sound
func make_rotor() -> void:
	var seg := 24
	var P := PackedVector3Array([Vector3.ZERO])
	var C := PackedColorArray([Color(0.1, 0.1, 0.1, 0.25)])
	var I := PackedInt32Array()
	var r: float = spec["rotor_r"]
	for i in seg:
		var a := i * TAU / seg
		P.append(Vector3(cos(a), 0, sin(a)) * r)
		C.append(Color(0.1, 0.1, 0.1, 0.05))
		I.append_array([0, 1 + i, 1 + (i + 1) % seg])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = P
	arr[Mesh.ARRAY_COLOR] = C
	arr[Mesh.ARRAY_INDEX] = I
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.vertex_color_use_as_albedo = true
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	rotor_disc = MeshInstance3D.new()
	rotor_disc.mesh = m
	rotor_disc.material_override = mat
	rotor_disc.position = spec["rotor"] + Vector3.UP * 0.05
	rotor_disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	rotor_disc.visible = false
	add_child(rotor_disc)


func _glow(name: String, pts: Array, cols: Array, sizes: Array, night_only: bool) -> MeshInstance3D:
	var P := PackedVector3Array()
	var U := PackedVector2Array()
	var U2 := PackedVector2Array()
	var C := PackedColorArray()
	var I := PackedInt32Array()
	var cr := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
	for i in pts.size():
		for k in 4:
			P.append(pts[i])
			U.append(cr[k])
			U2.append(Vector2(sizes[i], 0))
			C.append(cols[i])
		I.append_array([i * 4, i * 4 + 1, i * 4 + 2, i * 4, i * 4 + 2, i * 4 + 3])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = P
	arr[Mesh.ARRAY_TEX_UV] = U
	arr[Mesh.ARRAY_TEX_UV2] = U2
	arr[Mesh.ARRAY_COLOR] = C
	arr[Mesh.ARRAY_INDEX] = I
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.mesh = m
	mi.custom_aabb = AABB(Vector3.ONE * -(spec["length"] + 2.0), Vector3.ONE * (spec["length"] + 2.0) * 2.0)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/glow.gdshader")
	mat.set_shader_parameter("tex", Ui.tex("glow"))
	mat.set_shader_parameter("night", 1.0)
	mat.set_shader_parameter("boost", 1.5 if night_only else 2.0)
	mi.material_override = mat
	add_child(mi)
	return mi


func make_lights() -> void:
	var ls: Array = spec["lights"]
	if ls.is_empty():
		return
	var pts: Array = []
	var cols: Array = []
	var sizes: Array = []
	for l in ls:
		pts.append(l)
		cols.append(Color(1.0, 0.94, 0.82, 1.0))
		sizes.append(0.55)
	for l in ls:
		pts.append(Vector3(l.x, l.y, -l.z))
		cols.append(Color(1.0, 0.12, 0.08, 0.8))
		sizes.append(0.3)
	lights = _glow("lights", pts, cols, sizes, true)
	lights.visible = false
	if spec["police"]:
		var h: float = spec["height"]
		siren_node = _glow("siren", [Vector3(-0.35, h + 0.05, 0), Vector3(0.35, h + 0.05, 0)],
			[Color(1, 0.12, 0.12), Color(0.16, 0.31, 1.0)], [0.7, 0.7], false)
		siren_node.visible = false


func _process(delta: float) -> void:
	# no ground collision loaded here yet: hold still instead of falling through the map
	if not traffic and G.city:
		var ready: bool = G.city.collision_ready(global_position)
		if not ready and not freeze:
			freeze = true
			frozen_wait = true
		elif ready and frozen_wait:
			freeze = false
			frozen_wait = false
	if rotor_disc:
		rotor_disc.visible = is_heli() and rotor > 0.05
		rotor_disc.rotate_y(delta * 30.0 * rotor)
	if lights:
		lights.visible = not wrecked and (driver != null or npc_driver or traffic) and G.env.night > 0.3
	if siren_node:
		var on := siren and not wrecked
		siren_node.visible = on
		if on:
			siren_node.scale = Vector3(1.0 if sin(G.now * 14.0) > 0.0 else -1.0, 1.0, 1.0)
	if wrecked:
		burning += delta
		if burning < 5.0 and randf() < 0.3:
			Fx.flash(global_transform * Vector3(0, spec["height"] * 0.7, -spec["length"] * 0.3), 1.2, Color(1.0, 0.45, 0.1), 0.15)
		if burning > 5.0 and burning - delta <= 5.0:
			Combat.explode(global_position, 8.0, 120.0, null)
			if not freeze:
				apply_central_impulse(Vector3.UP * spec["mass"] * 6.0)
	# people in the way of the player's vehicle (and the player in the way of traffic)
	if (driver and driver.is_player) or traffic:
		hit_people()
	sound(delta)


func hit_people() -> void:
	var sp := speed()
	if sp < 3.0:
		return
	var inv := global_transform.affine_inverse()
	var hx: float = spec["width"] * 0.5 + 0.3
	var hz: float = spec["length"] * 0.5 + 0.3
	var mine := driver != null and driver.is_player
	for h in Human.all:
		if h == driver or h.vehicle == self or h.dead:
			continue
		if not mine and not h.is_player:
			continue
		var d: Vector3 = h.global_position - global_position
		if d.length_squared() > (hz + 2.0) * (hz + 2.0):
			continue
		var local: Vector3 = inv * h.global_position
		if absf(local.x) < hx and absf(local.z) < hz and local.y > -1.0 and local.y < 2.5:
			h.hit_by_vehicle(self, sp)
			if mine and not h.is_player:
				Wanted.crime(1.2 if h.police else 0.3, h.global_position, h.police)


func sound(delta: float) -> void:
	var lis: Vector3 = G.cam.cam.global_position if G.cam else global_position
	var want := not wrecked and (driver != null or npc_driver or (is_heli() and rotor > 0.05)) and lis.distance_squared_to(global_position) < 45.0 * 45.0
	if want and engine == null:
		var c := "engine_car"
		if is_heli():
			c = "engine_heli"
		elif is_boat():
			c = "engine_boat"
		elif is_bike():
			c = "engine_bike"
		elif spec["cls"] == "trike":
			c = "engine_auto"
		elif spec["name"] == "bus" or spec["name"] == "truck":
			c = "engine_diesel"
		engine = G.audio.loop(c, self)
	if not want and engine:
		engine.queue_free()
		engine = null
	if engine == null:
		return
	var top: float = spec["top"] / 3.6
	var x := clampf(speed() / maxf(5.0, top), 0.0, 1.0)
	var mine := driver != null and driver.is_player
	if is_heli():
		engine.pitch_scale = 0.7 + 0.35 * rotor
		engine.volume_db = linear_to_db(maxf(0.001, 0.8 * rotor * G.audio.sfx))
		return
	engine_vol = lerpf(engine_vol, (0.55 if mine else 0.3) + 0.35 * absf(throttle), delta * 4.0)
	engine.volume_db = linear_to_db(maxf(0.001, engine_vol * G.audio.sfx))
	engine.pitch_scale = 0.75 + x * 0.9 + (absf(throttle) * 0.1 if mine else 0.0)


func horn() -> void:
	var h := "horn_car"
	if is_bike() or spec["cls"] == "trike":
		h = "horn_bike"
	elif spec["name"] == "bus" or spec["name"] == "truck":
		h = "horn_truck"
	G.audio.at(h, global_position, 0.9, 1.0, 10.0)
	Traffic.panic(global_position + forward() * 6.0, 6.0, false)


func set_kinematic_pose(p: Vector3, b: Basis, spd: float) -> void:
	kin_speed = spd
	global_transform = Transform3D(b, p)
