class_name Combat
extends RefCounted
## The weapons, shooting, melee hits, explosions.

enum { FIST, BAT, KNIFE, REVOLVER, PISTOL, SMG, SHOTGUN, AK47, SNIPER }

const DEFS := [
	{"id": FIST, "name": "Fists", "model": "", "icon": "fist", "sound": "punch", "melee": true, "rifle": false, "damage": 9.0, "range": 1.5, "rate": 2.2, "spread": 0.0, "pellets": 1, "mag": 0, "price": 0, "ammo_price": 0, "ammo_pack": 0},
	{"id": BAT, "name": "Baseball Bat", "model": "bat", "icon": "bat", "sound": "bat_hit", "melee": true, "rifle": false, "damage": 28.0, "range": 1.9, "rate": 1.4, "spread": 0.0, "pellets": 1, "mag": 0, "price": 1500, "ammo_price": 0, "ammo_pack": 0},
	{"id": KNIFE, "name": "Knife", "model": "knife", "icon": "knife", "sound": "knife_slash", "melee": true, "rifle": false, "damage": 38.0, "range": 1.6, "rate": 1.8, "spread": 0.0, "pellets": 1, "mag": 0, "price": 900, "ammo_price": 0, "ammo_pack": 0},
	{"id": REVOLVER, "name": "Revolver", "model": "revolver", "icon": "revolver", "sound": "shot_revolver", "melee": false, "rifle": false, "damage": 55.0, "range": 70.0, "rate": 1.5, "spread": 1.2, "pellets": 1, "mag": 6, "price": 8000, "ammo_price": 300, "ammo_pack": 18},
	{"id": PISTOL, "name": "Pistol", "model": "pistol", "icon": "pistol", "sound": "shot_pistol", "melee": false, "rifle": false, "damage": 30.0, "range": 60.0, "rate": 3.5, "spread": 2.0, "pellets": 1, "mag": 15, "price": 15000, "ammo_price": 450, "ammo_pack": 30},
	{"id": SMG, "name": "Carbine", "model": "smg", "icon": "smg", "sound": "shot_smg", "melee": false, "rifle": true, "damage": 22.0, "range": 75.0, "rate": 10.0, "spread": 3.2, "pellets": 1, "mag": 30, "price": 45000, "ammo_price": 900, "ammo_pack": 90},
	{"id": SHOTGUN, "name": "Shotgun", "model": "shotgun", "icon": "shotgun", "sound": "shot_shotgun", "melee": false, "rifle": true, "damage": 15.0, "range": 32.0, "rate": 1.1, "spread": 6.5, "pellets": 8, "mag": 6, "price": 60000, "ammo_price": 700, "ammo_pack": 18},
	{"id": AK47, "name": "AK-47", "model": "ak47", "icon": "ak47", "sound": "shot_smg", "melee": false, "rifle": true, "damage": 32.0, "range": 90.0, "rate": 8.0, "spread": 2.4, "pellets": 1, "mag": 30, "price": 85000, "ammo_price": 1200, "ammo_pack": 90},
	{"id": SNIPER, "name": "Sniper Rifle", "model": "sniper", "icon": "sniper", "sound": "shot_revolver", "melee": false, "rifle": true, "damage": 120.0, "range": 160.0, "rate": 0.8, "spread": 0.3, "pellets": 1, "mag": 5, "price": 120000, "ammo_price": 1500, "ammo_pack": 15},
]

const SHOT_MASK := G.L_WORLD | G.L_VEHICLE | G.L_PED | G.L_PLAYER


static func defn(w: int) -> Dictionary:
	return DEFS[w]


static func _owner_of(n: Object) -> Node:
	var p := n as Node
	while p:
		if p is Human or p is Vehicle:
			return p
		p = p.get_parent()
	return null


## One shot (or one shotgun blast) from 'origin' towards 'aim'.
static func fire(shooter: Human, w: Dictionary, origin: Vector3, aim: Vector3, extra_spread := 0.0) -> void:
	Fx.flash(origin, 0.35, Color(1.0, 0.75, 0.35), 0.06)
	if G.audio:
		G.audio.at(w["sound"], origin, 1.0, randf_range(0.95, 1.05), 8.0)
	var space := G.city.get_world_3d().direct_space_state
	var exclude: Array[RID] = []
	if shooter:
		exclude.append(shooter.get_rid())
		if shooter.vehicle:
			exclude.append(shooter.vehicle.get_rid())
	for p in int(w["pellets"]):
		var dir := (aim - origin).normalized()
		var sp: float = w["spread"] + extra_spread
		dir = dir.rotated(Vector3.UP, deg_to_rad(randf_range(-sp, sp)))
		var side := dir.cross(Vector3.UP).normalized()
		if side.length() > 0.1:
			dir = dir.rotated(side, deg_to_rad(randf_range(-sp, sp)))
		var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * float(w["range"]), SHOT_MASK, exclude)
		var hit := space.intersect_ray(q)
		var guard := 0
		while hit and guard < 4:
			var o := _owner_of(hit["collider"])
			if o is Human and (o.dead or o == shooter):
				exclude.append(hit["rid"])
				q.exclude = exclude
				hit = space.intersect_ray(q)
				guard += 1
				continue
			break
		if not hit:
			continue
		var target := _owner_of(hit["collider"])
		if target is Human:
			target.hurt(w["damage"], origin, shooter, false)
		elif target is Vehicle:
			target.damage(w["damage"] * 0.6, shooter)
			Fx.flash(hit["position"], 0.25, Color(1.0, 0.85, 0.5), 0.08)
		else:
			Fx.flash(hit["position"] + hit["normal"] * 0.05, 0.18, Color(1.0, 0.9, 0.7), 0.07)
			if p == 0 and G.audio:
				G.audio.at("bullet_impact", hit["position"], 0.5, 1.0, 4.0)
	Wanted.noise(origin, shooter)


static func _overlap(center: Vector3, radius: float, mask: int) -> Array:
	var space := G.city.get_world_3d().direct_space_state
	var q := PhysicsShapeQueryParameters3D.new()
	var s := SphereShape3D.new()
	s.radius = radius
	q.shape = s
	q.transform = Transform3D(Basis(), center)
	q.collision_mask = mask
	return space.intersect_shape(q, 32)


## A punch, bat swing or knife slash: hits the first person or vehicle in front.
static func melee(attacker: Human, w: Dictionary) -> bool:
	var c := attacker.global_position + attacker.facing() * (float(w["range"]) * 0.6) + Vector3.UP
	var target: Human = null
	var vt: Vehicle = null
	var bd := 1e9
	for r in _overlap(c, 0.85, SHOT_MASK & ~G.L_WORLD):
		var o := _owner_of(r["collider"])
		if o is Human and o != attacker and not o.dead:
			var d: float = o.global_position.distance_to(attacker.global_position)
			if d < bd:
				bd = d
				target = o
		elif o is Vehicle and vt == null:
			vt = o
	if target:
		target.hurt(w["damage"] * randf_range(0.85, 1.15), attacker.global_position, attacker, true)
		G.audio.at(w["sound"], c, 1.0, randf_range(0.9, 1.1), 5.0)
		return true
	if vt and w["id"] == BAT:
		vt.damage(8.0, attacker)
		G.audio.at("bat_hit", c, 0.8, 0.8, 5.0)
		return true
	G.audio.at("swing", c, 0.6, 1.0, 4.0)
	return false


static func explode(p: Vector3, radius: float, dmg: float, by: Human) -> void:
	Fx.flash(p + Vector3.UP, 6.0, Color(1.0, 0.55, 0.2), 0.5)
	Fx.flash(p + Vector3.UP * 2.0, 9.0, Color(1.0, 0.35, 0.1), 0.9)
	G.audio.at("explosion", p, 1.0, 1.0, 25.0)
	var done := {}
	for r in _overlap(p, radius, G.L_VEHICLE | G.L_PED | G.L_PLAYER):
		var o := _owner_of(r["collider"])
		if o == null or done.has(o):
			continue
		done[o] = true
		if o is Human:
			var k: float = 1.0 - o.global_position.distance_to(p) / radius
			o.hurt(dmg * clampf(k + 0.2, 0.0, 1.0), p, by, false)
		elif o is Vehicle:
			if not o.freeze:
				var away: Vector3 = (o.global_position - p + Vector3(0, 1.5, 0)).normalized()
				o.apply_central_impulse(away * o.spec["mass"] * 12.0 * clampf(1.0 - o.global_position.distance_to(p) / radius, 0.2, 1.0))
			o.damage(dmg * 6.0, by)
	if G.cam:
		G.cam.shake(0.6)
