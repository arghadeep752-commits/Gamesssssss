class_name Player
extends Human
## The player: walks, runs, jumps, swims, fights, shoots and drives.

static var I: Player

var move := Vector2.ZERO
var fire := false
var sprint := false
var jump := false
var vy := 0.0
var next_shot := 0.0
var next_step := 0.0
var aim_until := 0.0
var reload_until := 0.0
var last_ground := 0.0
var money := 25000
var owned := {}                       # weapon id -> true
var ammo: Array[int] = []
var clip: Array[int] = []
var swimming := false
var aim_target: Human = null
var near_vehicle: Vehicle = null
var outfit := "player_casual"
var speed_mul := 1.0
var gravity := -20.0
var active := true


static func create(parent: Node, pos: Vector3, yaw: float) -> Player:
	var p := Player.new()
	p.name = "Player"
	I = p
	G.player = p
	p.is_player = true
	parent.add_child(p)
	p.global_position = pos
	p.rotation.y = deg_to_rad(yaw)
	p.make_body(G.L_PLAYER, G.L_WORLD | G.L_VEHICLE, true)
	p.floor_max_angle = deg_to_rad(50)
	p.floor_snap_length = 0.3
	p.ammo.resize(Combat.DEFS.size())
	p.clip.resize(Combat.DEFS.size())
	for w in [Combat.FIST, Combat.BAT, Combat.KNIFE, Combat.REVOLVER]:
		p.owned[w] = true
	p.clip[Combat.REVOLVER] = 6
	p.ammo[Combat.REVOLVER] = 36
	p.set_model(p.outfit)
	return p


func set_outfit(o: String, t: Color) -> void:
	outfit = o
	tint = t
	set_model(o)
	if vehicle:
		show_body(vehicle.spec["open"])
		sit_anim()


func set_active(on: bool) -> void:
	active = on
	visible = on
	process_mode = Node.PROCESS_MODE_INHERIT if on else Node.PROCESS_MODE_DISABLED
	collision_layer = G.L_PLAYER if on else 0


## The land past the edge of the map is only scenery: keep the player (and the vehicle) inside.
func keep_inside(lim: float) -> bool:
	var n: Node3D = vehicle if vehicle else self
	var pos := n.global_position
	if absf(pos.x) <= lim and absf(pos.z) <= lim:
		return false
	var c := Vector3(clampf(pos.x, -lim, lim), pos.y, clampf(pos.z, -lim, lim))
	var o := G.flat(pos - c).normalized()
	if vehicle and not vehicle.freeze:
		vehicle.global_position = Vector3(c.x, pos.y, c.z)
		var v := vehicle.linear_velocity
		var ov := v.dot(o)
		if ov > 0.0:
			vehicle.linear_velocity = v - o * ov * 1.5
	elif vehicle == null:
		global_position = c
	return true


func teleport(p: Vector3, yaw: float) -> void:
	if vehicle:
		exit_vehicle(true)
	global_position = p
	rotation = Vector3(0, deg_to_rad(yaw), 0)
	velocity = Vector3.ZERO
	vy = 0.0


func revive() -> void:
	dead = false
	health = max_health
	knocked = 0.0
	collision_layer = G.L_PLAYER
	if rig:
		rig.play("idle", 0.0)


func total_ammo(w: int) -> int:
	return clip[w] + ammo[w]


func next_weapon(dir: int) -> void:
	var n := Combat.DEFS.size()
	var i := weapon
	for k in n:
		i = (i + dir + n) % n
		if owned.has(i) and (Combat.defn(i)["melee"] or total_ammo(i) > 0):
			equip(i)
			G.audio.ui("reload", 0.4)
			return


func _physics_process(delta: float) -> void:
	if G.game == null or G.game.state != G.game.S.PLAY:
		return
	if dead:
		if G.now - dead_time > 3.5:
			G.game.wasted()
		return
	if vehicle:
		in_vehicle(delta)
		return
	var cam_f: Vector3 = G.cam.flat() if G.cam else facing()
	var cam_r := Vector3(-cam_f.z, 0.0, cam_f.x)
	var wish := cam_r * move.x + cam_f * move.y
	var mag := clampf(wish.length(), 0.0, 1.0)
	if knocked > 0.0:
		knocked -= delta
		wish = Vector3.ZERO
		mag = 0.0
	var grounded := is_on_floor()
	if grounded:
		last_ground = G.now
	var wl: float = G.city.water_level(global_position.x, global_position.z)
	swimming = not is_nan(wl) and global_position.y < wl - 1.05
	var running := sprint and mag > 0.5 and not swimming
	var spd := 1.6 if swimming else (6.6 if running else (4.2 if mag > 0.75 else 1.7))
	spd *= speed_mul
	var vel := wish.normalized() * spd * mag
	if swimming:
		vy = move_toward(vy, (wl - 1.0 - global_position.y) * 3.0, 20.0 * delta)
	elif grounded:
		vy = -2.0
		if jump and knocked <= 0.0:
			vy = 6.2 * (1.6 if gravity > -10.0 else 1.0)
			jump = false
			G.audio.at("grunt", chest(), 0.25, 1.3, 3.0)
	else:
		vy += gravity * delta
	jump = false
	velocity = Vector3(vel.x, vy, vel.z)
	move_and_slide()
	if is_on_floor() and vy < 0.0:
		vy = -2.0

	# aiming: guns turn the body towards the target (or where the camera looks)
	var d := def()
	var aiming := fire or G.now < aim_until
	aim_target = find_target(d["range"]) if aiming and not d["melee"] else null
	if aiming and not swimming:
		var look: Vector3 = (aim_target.global_position - global_position) if aim_target else cam_f
		face_towards(look, 900.0, delta)
	elif mag > 0.05:
		face_towards(wish, 240.0 if swimming else 720.0, delta)
	if fire and not swimming and knocked <= 0.0:
		try_attack(d)

	# animation
	var c := "idle"
	var aspd := 1.0
	if knocked > 0.0:
		c = "hit"
	elif swimming:
		c = "swim"
	elif not grounded and G.now - last_ground > 0.25:
		c = "jump" if vy > 0.0 else "fall"
	elif mag < 0.05:
		c = "idle"
	elif running:
		c = "sprint"
		aspd = speed_mul
	elif mag > 0.75:
		c = "run"
		aspd = speed_mul
	else:
		c = "walk"
		aspd = lerpf(0.7, 1.1, mag)
	if rig:
		if (rig.current != "punch" and rig.current != "swing") or rig.is_finished():
			rig.play(c, 0.18, aspd)
		if not d["melee"] and aiming and not swimming:
			rig.set_upper("aim_rifle" if d["rifle"] else "aim_pistol", 1.0)
		else:
			rig.set_upper("")
	# footsteps
	if grounded and mag > 0.1 and not swimming and G.now > next_step:
		next_step = G.now + (0.28 if running else (0.34 if mag > 0.75 else 0.52)) / speed_mul
		G.audio.at("footstep_%d" % randi_range(1, 6), global_position, 0.55 if running else 0.35, randf_range(0.9, 1.1), 2.0)
	near_vehicle = find_vehicle(4.2)
	loot_bodies()
	if global_position.y < -40.0:
		teleport(G.game.spawn_point(), 0.0)


func try_attack(d: Dictionary) -> void:
	if G.now < next_shot or G.now < reload_until:
		return
	next_shot = G.now + 1.0 / d["rate"]
	aim_until = G.now + 1.2
	if d["melee"]:
		if rig:
			rig.play("punch" if d["id"] == Combat.FIST else "swing", 0.06, 1.2, true)
		get_tree().create_timer(0.18, false).timeout.connect(func():
			if is_instance_valid(self) and Combat.melee(self, d) and G.cam:
				G.cam.shake(0.1))
		return
	var w: int = d["id"]
	if clip[w] <= 0:
		if ammo[w] <= 0:
			G.audio.at("empty_click", muzzle(), 0.8, 1.0, 3.0)
			next_weapon(-1)
			return
		var take := mini(d["mag"], ammo[w])
		ammo[w] -= take
		clip[w] = take
		reload_until = G.now + 1.3
		G.audio.at("reload", muzzle(), 0.8, 1.2, 3.0)
		return
	clip[w] -= 1
	var aim: Vector3
	if aim_target:
		aim = aim_target.chest() + Vector3(randf_range(-0.15, 0.15), randf_range(-0.15, 0.15), randf_range(-0.15, 0.15))
	else:
		var f: Vector3 = G.cam.forward() if G.cam else facing()
		aim = muzzle() + f * float(d["range"])
	if rig:
		rig.set_upper("shoot_rifle" if d["rifle"] else "shoot_pistol", 1.0)
		rig.restart_upper()
	Combat.fire(self, d, muzzle(), aim, 0.0)
	if G.cam:
		G.cam.shake(0.35 if d["id"] == Combat.SHOTGUN else 0.12)


func find_target(rng: float) -> Human:
	var f: Vector3 = G.cam.flat() if G.cam else facing()
	var best: Human = null
	var bs := 1e9
	var space := get_world_3d().direct_space_state
	for h in Human.all:
		if h == self or h.dead or (h.vehicle and not h.vehicle.spec["open"]):
			continue
		var dv: Vector3 = h.global_position - global_position
		var dist := dv.length()
		if dist > rng or dist < 0.5:
			continue
		var ang := rad_to_deg(f.angle_to(G.flat(dv)))
		if ang > 40.0:
			continue
		var score := dist * (1.0 + ang / 20.0) * (0.6 if h.police and Wanted.stars > 0 else 1.0)
		if score >= bs:
			continue
		var q := PhysicsRayQueryParameters3D.create(chest(), h.chest(), G.L_WORLD)
		if space.intersect_ray(q):
			continue
		bs = score
		best = h
	return best


func find_vehicle(r: float) -> Vehicle:
	var best: Vehicle = null
	var bd := r
	for v in Vehicle.all:
		if v.wrecked or v.driver == self:
			continue
		var local: Vector3 = v.global_transform.affine_inverse() * global_position
		var hx: float = v.spec["width"] * 0.5
		var hz: float = v.spec["length"] * 0.5
		var q := Vector2(maxf(0.0, absf(local.x) - hx), maxf(0.0, absf(local.z) - hz))
		var d := q.length()
		if d < bd:
			bd = d
			best = v
	return best


func loot_bodies() -> void:
	for h in Human.all:
		if not h.dead or h.looted or h == self:
			continue
		if h.global_position.distance_squared_to(global_position) > 2.2:
			continue
		h.looted = true
		add_money(randi_range(300, 900) if h.police else randi_range(40, 650))


func add_money(amount: int) -> void:
	money = maxi(0, money + amount)
	if amount > 0:
		G.audio.ui("cash", 0.6)
		Hud.toast("+ ₹ " + G.rupees(amount), Color(0.4, 1.0, 0.45))


# ------------------------------------------------------------------ vehicles
func enter_vehicle(v: Vehicle) -> void:
	if v == null or v.wrecked:
		return
	if v.driver != null and v.driver != self:
		var d: Human = v.driver
		v.eject()
		if d is Ped:
			d.flee(global_position, 12.0)
		if v.spec["police"] or Wanted.cops_near(global_position, 40.0):
			Wanted.crime(1.2, global_position)
	G.note("enter " + v.spec["name"])
	vehicle = v
	v.take_driver(self)
	collision_layer = 0
	collision_mask = 0
	var old := global_transform
	get_parent().remove_child(self)
	v.add_child(self)
	position = v.seat_pos()
	rotation = Vector3.ZERO
	show_body(v.spec["open"])
	sit_anim()
	G.audio.at("engine_bike" if v.spec["open"] else "car_door", global_position, 0.6, 1.0, 4.0)
	G.game.on_enter_vehicle(v)


func sit_anim() -> void:
	if rig == null or vehicle == null:
		return
	rig.set_upper("")
	rig.play("ride" if vehicle.spec["cls"] == "bike" else "drive", 0.1)


func exit_vehicle(instant := false) -> void:
	if vehicle == null:
		return
	var v := vehicle
	G.note("exit " + v.spec["name"] + (" (thrown or teleported)" if instant else ""))
	var ex: Vector3 = v.global_transform * v.spec["exit"]
	if not instant:
		# the driver's door is on the right; use the left if something is in the way
		var q := PhysicsShapeQueryParameters3D.new()
		var cap := CapsuleShape3D.new()
		cap.radius = 0.3
		cap.height = 1.2
		q.shape = cap
		q.transform = Transform3D(Basis(), ex + Vector3.UP * 1.0)
		q.collision_mask = G.L_WORLD | G.L_VEHICLE
		q.exclude = [v.get_rid()]
		if not get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty():
			var e: Vector3 = v.spec["exit"]
			ex = v.global_transform * Vector3(-e.x, e.y, e.z)
	v.release_driver()
	vehicle = null
	var world: Node3D = G.game.world
	get_parent().remove_child(self)
	world.add_child(self)
	var gy: float = G.city.ground(ex, ex.y)
	var wl: float = G.city.water_level(ex.x, ex.z)
	if not is_nan(wl) and gy < wl:
		gy = maxf(gy, ex.y)
	global_position = Vector3(ex.x, maxf(gy, ex.y - 3.0) + 0.05, ex.z)
	rotation = Vector3(0, v.rotation.y, 0)
	collision_layer = G.L_PLAYER
	collision_mask = G.L_WORLD | G.L_VEHICLE
	show_body(true)
	if rig:
		rig.play("idle", 0.1)
	vy = 0.0
	velocity = Vector3.ZERO
	G.game.on_exit_vehicle(v)


func in_vehicle(_delta: float) -> void:
	position = vehicle.seat_pos()
	rotation = Vector3.ZERO
	if vehicle.wrecked and vehicle.burning > 2.0:
		exit_vehicle()
		return
	if fire and vehicle.spec["open"] and not def()["melee"] and G.now >= next_shot:
		aim_target = find_target(def()["range"])     # drive-by on bikes and autos
		if aim_target:
			try_attack(def())


func hurt(dmg: float, from: Vector3, by: Human, melee: bool) -> void:
	if G.game and G.game.god_mode:
		return
	super.hurt(dmg, from, by, melee)
	Hud.hurt_flash()


func die(by: Human) -> void:
	if vehicle:
		exit_vehicle(true)
	super.die(by)


func hit_by_vehicle(v: Vehicle, spd: float) -> void:
	if v.driver == self:
		return
	super.hit_by_vehicle(v, spd)
