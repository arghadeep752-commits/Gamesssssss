class_name Traffic
extends Node
## Spawns and removes traffic, pedestrians and police around the player; drives the traffic along the lanes.

static var I: Traffic

class TrafficCar:
	var v: Vehicle
	var lane := 0
	var s := 0.0
	var speed := 0.0
	var mood := 1.0
	var honk := 0.0
	var rider: Ped = null


class AIDriver:
	## Steers a police car towards the player.
	var v: Vehicle
	var stuck := 0.0
	var reverse_until := 0.0
	var dismounted := false


var lanes: Array = []
var walks: Array = []
var links: Array = []
var cars: Array = []
var peds: Array = []
var cop_cars: Array = []
var max_cars := 12
var max_peds := 16
var next := 0.0
const CAR_MODELS := ["auto_rickshaw", "e_rickshaw", "motorbike", "scooter", "car_hatch", "car_sedan", "car_suv", "van", "bus", "truck", "sports_car", "police_jeep"]
const CAR_WEIGHTS := [20, 9, 15, 12, 13, 8, 6, 5, 3, 5, 2, 2]
const PED_MODELS := ["npc_man", "npc_student", "npc_oldman", "npc_saree", "npc_tripuri"]
const PED_WEIGHTS := [30, 20, 14, 20, 16]
const PAINTS := [Color(1, 1, 1), Color(0.95, 0.95, 0.95), Color(0.75, 0.78, 0.82), Color(0.6, 0.62, 0.66),
	Color(1.0, 0.85, 0.8), Color(0.85, 0.9, 1.0), Color(1.0, 0.95, 0.8)]


func init_traffic() -> void:
	I = self
	G.traffic = self
	var m: Dictionary = G.city.meta
	var ls: Array = m.get("lanes", [])
	for o in ls:
		var p := Lane.from_points(o.get("pts", []))
		p.speed = float(o.get("speed", 12.0))
		p.cls = str(o.get("cls", "B"))
		p.junction = o.has("junction") or p.cls == "J"
		for k in o.get("next", []):
			var idx := int(k)
			if idx >= 0 and idx < ls.size():
				p.next.append(idx)
		lanes.append(p)
	for o in m.get("walks", []):
		walks.append(Lane.from_points(o.get("pts", [])))
	links.resize(walks.size() * 2)
	for i in links.size():
		links[i] = []
	for pair in m.get("walk_links", []):
		if pair.size() < 2:
			continue
		var a := _end(pair[0])
		var b := _end(pair[1])
		if a < 0 or b < 0 or a >= links.size() or b >= links.size():
			continue
		links[a].append(b)
		links[b].append(a)
	G.note("traffic: %d lanes, %d footpaths" % [lanes.size(), walks.size()])


static func _end(e) -> int:
	if e == null or e.size() < 2:
		return -1
	return int(e[0]) * 2 + (1 if float(e[1]) < 0.0 else 0)


static func _pick(names: Array, w: Array) -> String:
	var t := 0.0
	for x in w:
		t += x
	var r := randf() * t
	for i in names.size():
		r -= w[i]
		if r <= 0.0:
			return names[i]
	return names[0]


func next_walk(p: Ped, w: Lane) -> void:
	var end := p.path * 2 + (1 if p.s > w.len else 0)
	var opts: Array = links[end] if end < links.size() else []
	if opts.is_empty():
		p.dir = -p.dir
		p.s = clampf(p.s, 0.0, w.len)
		return
	var to: int = opts[randi() % opts.size()]
	p.path = to / 2
	var at_end := (to & 1) == 1
	p.s = walks[p.path].len if at_end else 0.0
	p.dir = -1.0 if at_end else 1.0


static func panic(at: Vector3, r: float, scream := true) -> void:
	if I == null:
		return
	var r2 := r * r
	for p in I.peds:
		if not is_instance_valid(p) or p.dead or p.police or p.st == Ped.RIDE or p.st == Ped.FIGHT:
			continue
		if p.global_position.distance_squared_to(at) < r2:
			if scream:
				p.flee(at, 8.0)
			elif p.st == Ped.WALK:
				p.st = Ped.IDLE
				p.until = G.now + 1.5


static func adopt(p: Ped) -> void:
	if I and not I.peds.has(p):
		I.peds.append(p)


static func reattach_ped(p: Ped) -> void:
	if I == null:
		return
	var best := 25.0
	var bp := -1
	var bs := 0.0
	for i in I.walks.size():
		var w: Lane = I.walks[i]
		var c := (w.p[0] + w.p[w.p.size() - 1]) * 0.5
		var lim := w.len * 0.5 + 30.0
		if c.distance_squared_to(p.global_position) > lim * lim:
			continue
		var n := w.nearest(p.global_position)
		if n[1] < best:
			best = n[1]
			bp = i
			bs = n[0]
	if bp >= 0:
		p.path = bp
		p.s = bs
		p.st = Ped.WALK
	else:
		p.path = -1
		p.st = Ped.IDLE
		p.until = G.now + 1e6


func _process(_delta: float) -> void:
	if G.game == null or Player.I == null or G.game.state == G.game.S.LOADING:
		return
	if G.now < next:
		return
	next = G.now + 0.25
	var pp: Vector3 = G.game.focus()
	for i in range(cars.size() - 1, -1, -1):
		var c: TrafficCar = cars[i]
		if c.v == null or not is_instance_valid(c.v):
			cars.remove_at(i)
			continue
		if c.v.global_position.distance_squared_to(pp) > 270.0 * 270.0:
			despawn(c)
	for i in range(peds.size() - 1, -1, -1):
		var p = peds[i]
		if not is_instance_valid(p):
			peds.remove_at(i)
			continue
		if p.st == Ped.RIDE:
			continue
		var d2: float = p.global_position.distance_squared_to(pp)
		var dead_long: bool = p.dead and G.now - p.dead_time > 40.0
		if d2 > 130.0 * 130.0 or dead_long:
			peds.remove_at(i)
			p.queue_free()
	for v in Vehicle.all.duplicate():
		if not is_instance_valid(v) or v.traffic or v.owned or (v.driver and v.driver.is_player):
			continue
		var d2: float = v.global_position.distance_squared_to(pp)
		if (v.wrecked and d2 > 120.0 * 120.0) or (not v.parked and d2 > 300.0 * 300.0):
			cop_cars.erase(v)
			v.queue_free()
	var tries := 3
	while cars.size() < max_cars and tries > 0:
		tries -= 1
		spawn_car(pp)
	var live := 0
	for p in peds:
		if is_instance_valid(p) and not p.police and p.st != Ped.RIDE:
			live += 1
	tries = 3
	while live < max_peds and tries > 0:
		tries -= 1
		if spawn_ped(pp):
			live += 1
	police(pp)


func _physics_process(delta: float) -> void:
	if G.game == null or G.game.state == G.game.S.LOADING:
		return
	for c in cars.duplicate():
		drive(c, delta)
	for v in cop_cars:
		if is_instance_valid(v) and v.ai:
			ai_drive(v.ai, delta)


func despawn(c: TrafficCar) -> void:
	cars.erase(c)
	if c.lane >= 0 and c.lane < lanes.size():
		lanes[c.lane].cars.erase(c)
	if c.rider and is_instance_valid(c.rider):
		peds.erase(c.rider)
		c.rider.queue_free()
	if c.v and is_instance_valid(c.v):
		c.v.queue_free()


func detach(c: TrafficCar) -> void:
	if c.lane >= 0 and c.lane < lanes.size():
		lanes[c.lane].cars.erase(c)
	cars.erase(c)
	if c.v and is_instance_valid(c.v):
		c.v.traffic = false
		c.v.tcar = null


func crash(c: TrafficCar, hit: Vector3) -> void:
	var v := c.v
	if v == null:
		return
	v.freeze = false
	v.linear_velocity = v.forward() * c.speed * 0.5 + hit * 0.3
	v.traffic = false
	v.release_driver()
	if c.rider:
		v.driver = c.rider
		v.eject()
	detach(c)


func _place(c: TrafficCar, L: Lane) -> void:
	var a := L.at(c.s)
	var pos: Vector3 = a[0]
	var ahead: Vector3 = L.at(minf(L.len, c.s + 2.5))[0]
	var fwd := ahead - pos
	if fwd.length_squared() < 0.01:
		fwd = a[1]
	var b := Basis.looking_at(fwd.normalized(), Vector3.UP)
	c.v.set_kinematic_pose(pos + Vector3.UP * 0.03, b, c.speed)


func drive(c: TrafficCar, dt: float) -> void:
	if c.v == null or not is_instance_valid(c.v) or not c.v.traffic:
		return
	var L: Lane = lanes[c.lane]
	var want := L.speed * c.mood * minf(1.0, c.v.spec["top"] / 110.0) * (0.6 if L.junction else 1.0)
	var gap := 1e9
	var my_len: float = c.v.spec["length"]
	for o in L.cars:
		if o != c and o.s > c.s and is_instance_valid(o.v):
			gap = minf(gap, o.s - c.s - (o.v.spec["length"] + my_len) * 0.5)
	if gap > 40.0 and L.next.size() > 0:
		for nx in L.next:
			for o in lanes[nx].cars:
				if is_instance_valid(o.v):
					gap = minf(gap, L.len - c.s + o.s - (o.v.spec["length"] + my_len) * 0.5)
	var obst := _obstacle(c)
	var g := minf(gap, obst)
	var safe := 4.0 + c.speed * 1.3
	if g < safe:
		want = minf(want, maxf(0.0, (g - 2.5) * 0.9))
	c.speed = move_toward(c.speed, want, (8.0 if want < c.speed else 2.6) * dt)
	if obst < 9.0 and c.speed < 1.0 and G.now > c.honk and randf() < 0.02:
		c.honk = G.now + 4.0
		c.v.horn()
	c.s += c.speed * dt
	var guard := 0
	while c.s > L.len and guard < 4:
		guard += 1
		if L.next.is_empty():
			despawn(c)
			return
		var nl: int = L.next[randi() % L.next.size()]
		L.cars.erase(c)
		c.s -= L.len
		c.lane = nl
		L = lanes[c.lane]
		L.cars.append(c)
	_place(c, L)


func _obstacle(c: TrafficCar) -> float:
	var best := 1e9
	var f := c.v.forward()
	var me := c.v.global_position
	var half: float = c.v.spec["length"] * 0.5
	var p := Player.I
	if p and not p.dead and p.active:
		var at: Vector3 = p.vehicle.global_position if p.vehicle else p.global_position
		var w: float = (p.vehicle.spec["width"] * 0.5 + 1.2) if p.vehicle else 1.6
		best = _check(at - me, f, half, w, best)
	for o in Vehicle.all:
		if o == c.v or o.traffic or o.global_position.distance_squared_to(me) > 400.0:
			continue
		best = _check(o.global_position - me, f, half, o.spec["width"] * 0.5 + 1.1, best)
	for h in peds:
		if not is_instance_valid(h) or h.dead or h.st == Ped.WALK or h.st == Ped.RIDE:
			continue
		var r: Vector3 = h.global_position - me
		if r.length_squared() > 400.0:
			continue
		best = _check(r, f, half, 1.4, best)
	return best


static func _check(rel: Vector3, f: Vector3, half: float, width: float, best: float) -> float:
	var along := rel.dot(f)
	if along < 0.0 or along > 22.0:
		return best
	var lat := G.flat(rel - f * along)
	if lat.length() > width:
		return best
	return minf(best, along - half)


func spawn_car(pp: Vector3) -> bool:
	if lanes.is_empty():
		return false
	var li := randi() % lanes.size()
	var L: Lane = lanes[li]
	if L.junction:
		return false
	var s := randf() * L.len
	var a := L.at(s)
	var pos: Vector3 = a[0]
	var d := pos.distance_to(pp)
	if d < 70.0 or d > 230.0:
		return false
	if G.cam and d < 140.0 and G.cam.visible_point(pos):
		return false
	for o in L.cars:
		if absf(o.s - s) < 18.0:
			return false
	var m := _pick(CAR_MODELS, CAR_WEIGHTS)
	if (m == "bus" or m == "truck") and L.cls == "C":
		m = "car_hatch"
	var v := Vehicle.spawn(G.game.world, m, pos, G.yaw_of(a[1]), true, PAINTS[randi() % PAINTS.size()])
	if v == null:
		return false
	var c := TrafficCar.new()
	c.v = v
	c.lane = li
	c.s = s
	c.mood = randf_range(0.8, 1.15)
	c.speed = L.speed * 0.6
	v.tcar = c
	L.cars.append(c)
	cars.append(c)
	_place(c, L)
	if v.spec["open"]:
		var rider := Ped.create(v, _pick(PED_MODELS, [40, 30, 15, 5, 10]), v.global_position, 0.0, false)
		rider.st = Ped.RIDE
		rider.vehicle = v
		rider.position = v.seat_pos()
		rider.rotation = Vector3.ZERO
		rider.collision_layer = 0
		if rider.rig:
			rider.rig.play("ride" if v.is_bike() else "drive", 0.0)
		v.driver = rider
		c.rider = rider
		peds.append(rider)
	else:
		v.npc_driver = true
	return true


func spawn_ped(pp: Vector3) -> bool:
	if walks.is_empty():
		return false
	var wi := randi() % walks.size()
	var w: Lane = walks[wi]
	var s := randf() * w.len
	var pos: Vector3 = w.at(s)[0]
	var d := pos.distance_to(pp)
	if d < 30.0 or d > 110.0:
		return false
	if G.cam and d < 55.0 and G.cam.visible_point(pos):
		return false
	var p := Ped.create(G.game.world, _pick(PED_MODELS, PED_WEIGHTS), pos, 0.0, false)
	p.path = wi
	p.s = s
	p.dir = 1.0 if randf() < 0.5 else -1.0
	peds.append(p)
	return true


func police(pp: Vector3) -> void:
	var stars := Wanted.stars
	var want_foot := 0 if stars == 0 else 1 + stars * 2
	var want_cars := 0 if stars == 0 else mini(4, stars)
	var foot := 0
	for p in peds:
		if is_instance_valid(p) and p.police and not p.dead and p.st == Ped.CHASE:
			foot += 1
	cop_cars = cop_cars.filter(func(c): return is_instance_valid(c) and not c.wrecked)
	if stars == 0:
		for c in cop_cars:
			if c.global_position.distance_squared_to(pp) > 150.0 * 150.0:
				c.queue_free()
		return
	if foot < want_foot and not walks.is_empty():
		for t in 6:
			var wi := randi() % walks.size()
			var pos: Vector3 = walks[wi].at(randf() * walks[wi].len)[0]
			var d := pos.distance_to(pp)
			if d < 35.0 or d > 75.0:
				continue
			var cop := Ped.create(G.game.world, "police", pos, 0.0, true)
			peds.append(cop)
			cop.chase()
			break
	if cop_cars.size() < want_cars and not lanes.is_empty():
		for t in 6:
			var li := randi() % lanes.size()
			var L: Lane = lanes[li]
			var a := L.at(randf() * L.len)
			var pos: Vector3 = a[0]
			var d := pos.distance_to(pp)
			if d < 80.0 or d > 160.0 or not G.city.collision_ready(pos):
				continue
			var v := Vehicle.spawn(G.game.world, "police_jeep", pos + Vector3.UP * 0.3, G.yaw_of(a[1]), false, Color.WHITE)
			if v == null:
				break
			v.parked = false
			v.handbrake = false
			v.brake = 0.0
			v.npc_driver = true
			v.siren = true
			var ai := AIDriver.new()
			ai.v = v
			v.ai = ai
			cop_cars.append(v)
			break


func ai_drive(a: AIDriver, dt: float) -> void:
	var p := Player.I
	var v := a.v
	if v == null or v.wrecked or p == null:
		return
	if Wanted.stars == 0 or p.dead:
		v.siren = false
		v.throttle = 0.0
		v.brake = 1.0
		return
	v.siren = true
	v.handbrake = false
	var target: Vector3 = p.vehicle.global_position if p.vehicle else p.global_position
	var local: Vector3 = v.global_transform.affine_inverse() * target
	var ang := rad_to_deg(atan2(local.x, -local.z))
	var dist := local.length()
	v.steer = clampf(ang / 28.0, -1.0, 1.0)
	if G.now < a.reverse_until:
		v.throttle = -0.8
		v.steer = -v.steer
		v.brake = 0.0
		return
	if dist < 14.0 and p.vehicle == null:
		v.throttle = 0.0
		v.brake = 1.0
		if not a.dismounted and v.speed() < 2.0:
			a.dismounted = true
			v.npc_driver = false
			for i in 2:
				var side: float = (v.spec["width"] * 0.5 + 0.8) * (1.0 if i == 0 else -1.0)
				var e: Vector3 = v.global_transform * Vector3(side, 0, 0)
				e.y = G.city.ground(e, v.global_position.y)
				var cop := Ped.create(G.game.world, "police", e, rad_to_deg(v.rotation.y), true)
				Traffic.adopt(cop)
				cop.chase()
		return
	if a.dismounted:
		v.throttle = 0.0
		v.brake = 1.0
		return
	v.brake = 0.0
	v.throttle = -0.7 if absf(ang) > 110.0 else (1.0 if dist > 35.0 else 0.75)
	if absf(ang) > 110.0:
		v.steer = -v.steer
	if v.speed() < 1.2 and v.throttle > 0.5:
		a.stuck += dt
	else:
		a.stuck = 0.0
	if a.stuck > 1.8:
		a.stuck = 0.0
		a.reverse_until = G.now + 1.4
