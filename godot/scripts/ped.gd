class_name Ped
extends Human
## People of Agartala: walk the footpaths, react to danger, sometimes fight back; police officers chase and shoot.

enum { WALK, FLEE, COWER, FIGHT, CHASE, DEAD, RIDE, IDLE }

var st := WALK
var path := 0
var s := 0.0
var dir := 1.0
var side := 0.0
var speed := 1.3
var until := 0.0
var next_shot := 0.0
var threat := Vector3.ZERO
var ground_y := 0.0
var next_ground := 0.0
var fearless := false


static func create(parent: Node, m: String, pos: Vector3, yaw: float, cop: bool) -> Ped:
	var p := Ped.new()
	p.name = "Police" if cop else "Ped"
	p.police = cop
	p.tint = Color.WHITE if cop else Color.from_hsv(randf(), randf_range(0.0, 0.25), randf_range(0.85, 1.0))
	parent.add_child(p)
	p.global_position = pos
	p.rotation.y = deg_to_rad(yaw)
	p.make_body(G.L_PED, 0)
	p.set_model(m)
	p.ground_y = pos.y
	p.side = randf_range(-0.9, 0.9)
	p.speed = randf_range(1.15, 1.5) * (0.75 if m == "npc_oldman" else 1.0)
	p.fearless = cop or ((m == "npc_man" or m == "npc_student") and randf() < 0.3)
	if cop:
		p.equip(Combat.PISTOL)
		p.health = 120.0
		p.max_health = 120.0
	return p


func flee(from: Vector3, time: float) -> void:
	if dead or st == RIDE or police:
		return
	threat = from
	if st != FLEE and randf() < 0.25:
		G.audio.at("scream", chest(), 0.7, randf_range(0.9, 1.2), 6.0)
	st = COWER if randf() < 0.2 else FLEE
	until = G.now + time * randf_range(0.8, 1.3)


func chase() -> void:
	if dead or st == RIDE:
		return
	st = CHASE


func hurt(dmg: float, from: Vector3, by: Human, melee: bool) -> void:
	super.hurt(dmg, from, by, melee)
	if dead:
		return
	if by and by.is_player:
		if police:
			Wanted.crime(1.5, global_position, true)
			chase()
		elif melee and fearless:
			st = FIGHT
			until = G.now + 20.0
		else:
			flee(from, 10.0)
		if not police:
			Wanted.crime(0.25, global_position)


func die(by: Human) -> void:
	super.die(by)
	st = DEAD
	if by and by.is_player:
		Wanted.crime(2.2 if police else 0.9, global_position, police)
	Traffic.panic(global_position, 25.0)


func _process(delta: float) -> void:
	if G.game == null:
		return
	var pl := Player.I
	var dp := global_position.distance_to(pl.global_position) if pl else 0.0
	var dc: float = global_position.distance_to(G.cam.cam.global_position) if G.cam else dp
	if rig:
		rig.update_every = 0.0 if dc < 25.0 else (0.066 if dc < 60.0 else 0.15)
	if st == DEAD or dead:
		if vehicle:
			vehicle.eject()
		return
	if st == RIDE:
		return
	if knocked > 0.0:
		knocked -= delta
		anim("hit", 1.0)
		return
	var vel := Vector3.ZERO
	match st:
		WALK:
			walk_path(delta)
		IDLE:
			anim("idle", 1.0)
			if G.now > until:
				st = WALK
		FLEE:
			var away := G.flat(global_position - threat)
			if away.length_squared() < 0.01:
				away = facing()
			vel = away.normalized() * 5.2
			if G.now > until:
				st = IDLE
				until = G.now + 2.0
				Traffic.reattach_ped(self)
		COWER:
			anim("cower", 1.0)
			if G.now > until:
				st = IDLE
				until = G.now + 1.0
		FIGHT, CHASE:
			vel = pursue(delta, pl, dp)
	if vel.length_squared() > 0.01:
		var p := global_position + vel * delta
		if G.now > next_ground:
			next_ground = G.now + 0.25
			ground_y = G.city.ground(p, ground_y)
		# stay out of buildings
		var space := get_world_3d().direct_space_state
		var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.8, global_position + Vector3.UP * 0.8 + vel.normalized() * 0.6, G.L_WORLD)
		if space.intersect_ray(q):
			vel = vel.rotated(Vector3.UP, deg_to_rad(90))
			p = global_position + vel * delta
		p.y = lerpf(global_position.y, ground_y, minf(1.0, 10.0 * delta))
		global_position = p
		face_towards(vel, 540.0, delta)
		var sp := G.flat(vel).length()
		anim("sprint" if sp > 4.5 else ("run" if sp > 2.4 else "walk"), 1.0 if sp > 4.5 else (sp / 3.9 if sp > 2.4 else sp / 1.45))


func anim(c: String, spd: float) -> void:
	if rig == null:
		return
	if (rig.current == "punch" or rig.current == "hit") and not rig.is_finished():
		return
	rig.play(c, 0.2, spd)


func walk_path(delta: float) -> void:
	var tr: Traffic = G.traffic
	if tr == null or path < 0 or path >= tr.walks.size():
		st = IDLE
		until = G.now + 999.0
		return
	var w: Lane = tr.walks[path]
	s += dir * speed * delta
	if s > w.len or s < 0.0:
		tr.next_walk(self, w)
	w = tr.walks[path]
	var at := w.at(s)
	var c: Vector3 = at[0]
	var d: Vector3 = at[1]
	var right := Vector3(-d.z, 0.0, d.x)
	var target := c + right * side * dir
	target.y = c.y
	if target.distance_to(global_position) > 6.0:
		global_position = target
		return
	global_position = target
	face_towards(d * dir, 360.0, delta)
	anim("walk", speed / 1.45)


func pursue(delta: float, pl: Player, dist: float) -> Vector3:
	if pl == null or pl.dead:
		st = IDLE
		until = G.now + 3.0
		return Vector3.ZERO
	if st == FIGHT and G.now > until:
		st = WALK
		Traffic.reattach_ped(self)
		return Vector3.ZERO
	if police and Wanted.stars == 0:
		st = IDLE
		until = G.now + 4.0
		Traffic.reattach_ped(self)
		return Vector3.ZERO
	var to := G.flat(pl.global_position - global_position)
	face_towards(to, 540.0, delta)
	if police:
		var space := get_world_3d().direct_space_state
		var see := dist < 32.0 and not space.intersect_ray(PhysicsRayQueryParameters3D.create(chest(), pl.chest(), G.L_WORLD))
		if see:
			Wanted.seen()
		if Wanted.stars <= 1 and dist < 1.7 and pl.vehicle == null:
			G.game.busted()
			return Vector3.ZERO
		if see and dist < 24.0 and (Wanted.stars >= 2 or pl.weapon != Combat.FIST):
			if rig:
				rig.set_upper("aim_pistol", 1.0)
			if G.now > next_shot:
				next_shot = G.now + randf_range(0.7, 1.3)
				var aim: Vector3 = (pl.vehicle.global_position + Vector3.UP) if pl.vehicle else pl.chest()
				Combat.fire(self, Combat.defn(Combat.PISTOL), muzzle(), aim, 5.0 - minf(3.0, Wanted.stars))
			if dist < 9.0:
				return Vector3.ZERO
			return to.normalized() * 2.0
		if rig:
			rig.set_upper("")
		return to.normalized() * (5.4 if dist > 6.0 else 2.5)
	if dist < 1.3:
		if G.now > next_shot:
			next_shot = G.now + 1.1
			if rig:
				rig.play("punch", 0.06, 1.1, true)
			if randf() < 0.6:
				pl.hurt(6.0, global_position, self, true)
			G.audio.at("punch", chest(), 0.8, 1.0, 4.0)
		return Vector3.ZERO
	return to.normalized() * 4.0
