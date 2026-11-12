class_name Boss
extends CharacterBody2D
## Reusable boss: intro, telegraphed multi-pattern AI, phase 2 at half health,
## damage reaction, defeat sequence and rewards. Patterns are picked per boss id.

signal defeated(boss: Boss)

const GRAVITY := 2200.0

var boss_id := "shadow_samurai"
var cfg := {}
var max_hp := 500.0
var hp := 500.0
var kind := "ninja"
var facing := -1.0
var phase := 1
var dead := false
var active := false
var dangerous := false
var contact_damage := 22.0
var arena := Vector2(0, 2000)   # x range
var sprite: AnimatedSprite2D
var fx_mat: ShaderMaterial
var player: Player
var _body_size := Vector2(80, 160)
var _contact: Area2D
var _last_patterns: Array = []
var _warn: Label
var _aura: CPUParticles2D
var _scale := 1.0
var _flying := false


static func create(id: String) -> Boss:
	var b := Boss.new()
	b.boss_id = id
	b.cfg = GameData.BOSSES[id]
	return b


func _ready() -> void:
	add_to_group("enemy")
	add_to_group("boss")
	collision_layer = 4
	collision_mask = 1
	kind = cfg.kind
	max_hp = float(cfg.hp)
	hp = max_hp
	_scale = float(cfg.scale)
	sprite = AnimatedSprite2D.new()
	add_child(sprite)
	if kind == "ninja":
		sprite.sprite_frames = SpriteLib.ninja_frames()
		var ch := SpriteLib.ninja_cell_height()
		sprite.offset = Vector2(0, -(ch / 2.0 - SpriteLib.ninja_foot_margin()))
		sprite.scale = Vector2(_scale, _scale)
		fx_mat = SpriteLib.make_fx_material(cfg.cloth_hue, cfg.cloth_sat, cfg.cloth_val, cfg.armor)
		_body_size = Vector2(44 * _scale, 90 * _scale)
		contact_damage = 24.0
		sprite.play("idle")
	else:
		sprite.sprite_frames = SpriteLib.critter_frames(kind, true)
		sprite.offset = Vector2(0, -64)
		sprite.scale = Vector2(_scale / 2.0, _scale / 2.0)
		fx_mat = SpriteLib.make_fx_material(-1.0, 1.0, 1.0, Color.WHITE, cfg.get("hue_shift", 0.0), 1.0)
		sprite.modulate = cfg.get("tint", Color.WHITE)
		_body_size = Vector2(64 * _scale * 0.78, 64 * _scale * 0.72)
		contact_damage = 26.0
		sprite.play("idle")
	sprite.material = fx_mat
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = _body_size
	cs.shape = r
	cs.position = Vector2(0, -_body_size.y / 2.0)
	add_child(cs)
	_contact = Area2D.new()
	_contact.collision_layer = 0
	_contact.collision_mask = 2
	_contact.monitorable = false
	var ccs := CollisionShape2D.new()
	var cr := RectangleShape2D.new()
	cr.size = _body_size * 0.85
	ccs.shape = cr
	ccs.position = cs.position
	_contact.add_child(ccs)
	add_child(_contact)
	_warn = UITheme.make_title("!", 72, Color(1, 0.3, 0.2))
	_warn.position = Vector2(-20, -_body_size.y - 110)
	_warn.visible = false
	add_child(_warn)
	_build_aura()


func _build_aura() -> void:
	if int(SaveManager.setting("quality")) == 0:
		return
	var col := Color(0.6, 0.2, 0.9)
	var tex := "smoke_04"
	match boss_id:
		"shadow_samurai":
			col = Color(0.8, 0.1, 0.15, 0.7)
		"demon_ronin":
			col = Color(1.0, 0.35, 0.1, 0.8)
			tex = "flame_01"
		"ice_guardian":
			col = Color(0.6, 0.9, 1.0, 0.8)
			tex = "star_04"
		"temple_beast":
			col = Color(0.7, 0.5, 1.0, 0.7)
		"fire_lord":
			col = Color(1.0, 0.5, 0.15, 0.85)
			tex = "flame_01"
		"shadow_king":
			col = Color(0.55, 0.2, 0.95, 0.85)
	_aura = CPUParticles2D.new()
	_aura.amount = 16
	_aura.lifetime = 1.0
	_aura.texture = SpriteLib.tex("res://assets/effects/%s.png" % tex)
	_aura.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_aura.emission_rect_extents = _body_size * 0.45
	_aura.position = Vector2(0, -_body_size.y / 2.0)
	_aura.direction = Vector2(0, -1)
	_aura.gravity = Vector2(0, -80)
	_aura.initial_velocity_min = 10
	_aura.initial_velocity_max = 50
	_aura.scale_amount_min = 0.1
	_aura.scale_amount_max = 0.25
	_aura.color = col
	_aura.local_coords = false
	_aura.material = Effects.add_material()
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	_aura.color_ramp = ramp
	add_child(_aura)
	move_child(_aura, 0)


func _physics_process(delta: float) -> void:
	if player == null or not is_instance_valid(player):
		player = get_tree().get_first_node_in_group("player")
	if not is_on_floor() and not _flying:
		velocity.y = min(velocity.y + GRAVITY * delta, 1500.0)
	move_and_slide()
	global_position.x = clampf(global_position.x, arena.x + _body_size.x / 2.0, arena.y - _body_size.x / 2.0)
	if kind == "ninja":
		sprite.flip_h = facing < 0.0
	else:
		sprite.flip_h = facing > 0.0
	if active and not dead:
		for b in _contact.get_overlapping_bodies():
			if b is Player:
				var p: Player = b
				if kind != "ninja" and p.velocity.y > 80.0 and p.global_position.y < global_position.y - _body_size.y * 0.6:
					continue
				p.take_damage(contact_damage * (1.3 if dangerous else 1.0), global_position, 620.0, false)



# ------------------------------------------------------------------ AI
func start_fight() -> void:
	active = true
	Events.boss_health_changed.emit(hp, max_hp)
	_run_ai()


func _run_ai() -> void:
	await _wait(0.6)
	while not dead and active:
		if player == null or player.is_dead():
			await _wait(0.5)
			continue
		var pat := _choose_pattern()
		await _do_pattern(pat)
		if dead:
			return
		var rest := (0.9 if phase == 1 else 0.55) * randf_range(0.8, 1.2)
		play("idle")
		await _wait(rest)


func _patterns() -> Array:
	match boss_id:
		"shadow_samurai":
			return ["dash_slash", "jump_slash", "kunai_fan"]
		"demon_ronin":
			return ["dash_slash", "jump_slash", "fire_kunai", "dash_slash"] if phase == 1 else ["triple_dash", "jump_slash", "fire_kunai", "kunai_rain"]
		"ice_guardian":
			return ["hop_slam", "ice_shards", "slide_charge"]
		"temple_beast":
			return ["roll_charge", "spike_burst", "hop_slam"] if phase == 1 else ["roll_charge", "spike_burst", "summon", "hop_slam"]
		"fire_lord":
			return ["fireball_arcs", "lava_rain", "flame_wave", "hop_slam"]
		"shadow_king":
			return ["teleport_strike", "kunai_storm", "dash_slash"] if phase == 1 else ["teleport_strike", "shadow_clones", "kunai_storm", "triple_dash", "jump_slash"]
	return ["dash_slash"]


func _choose_pattern() -> String:
	var opts := _patterns()
	var pick: String = opts[randi() % opts.size()]
	if _last_patterns.size() >= 2 and _last_patterns[-1] == pick and _last_patterns[-2] == pick:
		pick = opts[(opts.find(pick) + 1) % opts.size()]
	_last_patterns.append(pick)
	return pick


func _do_pattern(p: String) -> void:
	match p:
		"dash_slash":
			await _p_dash(1)
		"triple_dash":
			await _p_dash(3)
		"jump_slash":
			await _p_jump_slash()
		"kunai_fan":
			await _p_kunai_fan(false)
		"fire_kunai":
			await _p_kunai_fan(true)
		"kunai_rain":
			await _p_sky_rain("big_kunai", 7)
		"teleport_strike":
			await _p_teleport()
		"shadow_clones":
			await _p_summon("ninja", 2)
		"kunai_storm":
			await _p_storm()
		"hop_slam":
			await _p_hop_slam()
		"ice_shards":
			await _p_sky_rain("icespike", 6)
		"slide_charge":
			await _p_charge(1)
		"roll_charge":
			await _p_charge(2)
		"spike_burst":
			await _p_storm()
		"summon":
			await _p_summon("spike_slime", 2)
		"fireball_arcs":
			await _p_fireball_arcs()
		"lava_rain":
			await _p_sky_rain("boss_fireball", 6)
		"flame_wave":
			await _p_flame_wave()


# ------------------------------------------------------------ patterns
func _p_dash(times: int) -> void:
	for i in times:
		if dead:
			return
		_face_player()
		play("idle" if kind == "ninja" else "idle")
		await _telegraph(0.55 if phase == 1 else 0.4)
		if dead:
			return
		play("attack" if kind == "ninja" else "move")
		dangerous = true
		AudioManager.play_sfx("swing2", 0.1)
		velocity.x = facing * (1150.0 if phase == 1 else 1300.0)
		var t := 0.0
		while t < 0.36 and not dead:
			await get_tree().physics_frame
			t += get_physics_process_delta_time()
			_afterimage()
			if is_on_wall():
				break
		dangerous = false
		velocity.x = 0.0
		Effects.slash(get_parent(), global_position + Vector2(facing * 60, -_body_size.y * 0.5), facing, Color(1, 0.4, 0.4), 1.6)
		await _wait(0.25)


func _p_jump_slash() -> void:
	_face_player()
	await _telegraph(0.45)
	if dead:
		return
	var target_x := player.global_position.x
	var dx := target_x - global_position.x
	velocity = Vector2(clampf(dx * 1.4, -900, 900), -1250.0)
	play("jump" if kind == "ninja" else "jump")
	await _wait(0.25)
	play("jump_attack" if kind == "ninja" else "jump")
	while not dead and not is_on_floor():
		await get_tree().physics_frame
	velocity.x = 0.0
	if dead:
		return
	_land_shockwave(Color(1, 0.4, 0.3))
	await _wait(0.35)


func _p_kunai_fan(fire: bool) -> void:
	for wave in (1 if phase == 1 else 2):
		_face_player()
		await _telegraph(0.4)
		if dead:
			return
		play("throw" if kind == "ninja" else "idle")
		await _wait(0.15)
		var base := (player.global_position + Vector2(0, -50) - (global_position + Vector2(0, -_body_size.y * 0.55))).angle()
		var count := 5 if not fire else 6
		for i in count:
			var ang := base + deg_to_rad(-24 + i * (48.0 / (count - 1)))
			var opts := {"life": 2.0, "color": Color(1, 0.6, 0.3) if fire else Color(1, 1, 1)}
			Projectile.spawn(get_parent(), "kunai", global_position + Vector2(facing * 40, -_body_size.y * 0.55), Vector2.from_angle(ang) * 700.0, 16.0, "enemy", opts)
		AudioManager.play_sfx("throw", 0.05)
		await _wait(0.45)


func _reposition_hop() -> void:
	# big creatures hop toward the arena centre before casting, keeping fights dynamic
	var mid := (arena.x + arena.y) / 2.0
	var dir := signf(mid - global_position.x)
	if dir == 0.0:
		dir = -facing
	velocity = Vector2(dir * 380.0, -700.0)
	play("jump")
	await _wait(0.15)
	while not dead and not is_on_floor():
		await get_tree().physics_frame
	velocity.x = 0.0


func _p_sky_rain(proj: String, count: int) -> void:
	if kind != "ninja":
		await _reposition_hop()
		if dead:
			return
	play("attack" if kind == "ninja" else "idle")
	await _telegraph(0.35)
	if dead:
		return
	var xs := []
	for i in count + (2 if phase == 2 else 0):
		xs.append(clampf(player.global_position.x + randf_range(-420, 420), arena.x + 60, arena.y - 60))
	var ground_y := global_position.y
	for x in xs:
		_ground_marker(Vector2(x, ground_y), 0.8)
	await _wait(0.8)
	if dead:
		return
	for x in xs:
		var p := Projectile.spawn(get_parent(), proj, Vector2(x, ground_y - 900.0), Vector2(0, 900.0), 18.0, "enemy",
			{"through_walls": true, "life": 1.3, "scale": 1.3 if proj != "boss_fireball" else 0.8})
		if proj == "icespike" or proj == "big_kunai":
			p.rotation = PI / 2.0
	AudioManager.play_sfx("magic", 0.05)
	await _wait(0.7)


func _p_teleport() -> void:
	for i in (1 if phase == 1 else 2):
		var tw := create_tween()
		tw.tween_method(func(v): fx_mat.set_shader_parameter("dissolve", v), 0.0, 1.0, 0.25)
		await tw.finished
		if dead:
			return
		var side := -signf(player.facing) if player.facing != 0 else 1.0
		global_position = Vector2(clampf(player.global_position.x + side * 140.0, arena.x + 80, arena.y - 80), player.global_position.y - 40)
		velocity = Vector2.ZERO
		_face_player()
		var tw2 := create_tween()
		tw2.tween_method(func(v): fx_mat.set_shader_parameter("dissolve", v), 1.0, 0.0, 0.2)
		await tw2.finished
		await _telegraph(0.35)
		if dead:
			return
		play("attack")
		AudioManager.play_sfx("swing1", 0.1)
		await _wait(0.12)
		Effects.slash(get_parent(), global_position + Vector2(facing * 80, -_body_size.y * 0.5), facing, Color(0.7, 0.4, 1.0), 2.0)
		var d := player.global_position - global_position
		if absf(d.x) < 190.0 and absf(d.y) < 180.0:
			player.take_damage(26.0, global_position, 650.0, false)
		await _wait(0.4)


func _p_summon(enemy_id: String, count: int) -> void:
	play("throw" if kind == "ninja" else "idle")
	await _telegraph(0.5)
	if dead:
		return
	for i in count:
		var x := clampf(global_position.x + (i * 2 - 1) * 180.0, arena.x + 80, arena.y - 80)
		get_tree().call_group("game", "spawn_enemy", enemy_id, Vector2(x, global_position.y - 10))
		Effects.flash(get_parent(), Vector2(x, global_position.y - 50), "magic_02", Color(0.7, 0.4, 1, 0.9), 0.3, 1.6, 0.4)
	AudioManager.play_sfx("spirit", 0.0)
	await _wait(0.6)


func _p_storm() -> void:
	play("throw" if kind == "ninja" else "idle")
	await _telegraph(0.55)
	if dead:
		return
	var n := 10 if phase == 1 else 14
	var proj := "shadow_orb" if boss_id == "shadow_king" else "big_kunai"
	for ring in (1 if phase == 1 else 2):
		var offset := randf() * TAU
		for i in n:
			var ang := offset + TAU * i / n
			var p := Projectile.spawn(get_parent(), proj, global_position + Vector2(0, -_body_size.y * 0.5), Vector2.from_angle(ang) * 460.0, 16.0, "enemy", {"through_walls": true, "life": 2.2})
			p.rotation = ang
		AudioManager.play_sfx("magic", 0.05)
		await _wait(0.45)


func _p_hop_slam() -> void:
	for i in (1 if phase == 1 else 2):
		_face_player()
		play("idle")
		await _telegraph(0.45)
		if dead:
			return
		var dx := player.global_position.x - global_position.x
		velocity = Vector2(clampf(dx * 1.3, -800, 800), -1350.0)
		play("jump")
		await _wait(0.2)
		while not dead and not is_on_floor():
			await get_tree().physics_frame
		velocity.x = 0.0
		if dead:
			return
		_land_shockwave(Color(0.7, 0.9, 1.0) if boss_id == "ice_guardian" else Color(1, 0.6, 0.3))
		await _wait(0.35)


func _p_charge(bounces: int) -> void:
	_face_player()
	play("move")
	await _telegraph(0.5)
	if dead:
		return
	dangerous = true
	var left := bounces
	velocity.x = facing * 900.0
	var t := 0.0
	while not dead and t < 3.0:
		await get_tree().physics_frame
		t += get_physics_process_delta_time()
		velocity.x = facing * 900.0
		sprite.rotation += facing * 0.25 if boss_id == "temple_beast" else 0.0
		if is_on_wall() or global_position.x <= arena.x + _body_size.x / 2.0 + 2 or global_position.x >= arena.y - _body_size.x / 2.0 - 2:
			Events.camera_shake.emit(8.0, 0.2)
			AudioManager.play_sfx("boss_stomp", 0.1)
			left -= 1
			if left < 0:
				break
			facing = -facing
	dangerous = false
	sprite.rotation = 0.0
	velocity.x = 0.0
	await _wait(0.3)


func _p_fireball_arcs() -> void:
	# reposition with a hop before the volley so the Fire Lord keeps the arena moving
	var away := -signf(player.global_position.x - global_position.x)
	velocity = Vector2(away * 420.0, -760.0)
	play("jump")
	await _wait(0.15)
	while not dead and not is_on_floor():
		await get_tree().physics_frame
	velocity.x = 0.0
	for i in (3 if phase == 1 else 5):
		_face_player()
		await _telegraph(0.25)
		if dead:
			return
		var d := player.global_position - global_position
		var time := 1.0
		var v := Vector2(d.x / time, (d.y - 0.5 * 1100.0 * time * time) / time)
		Projectile.spawn(get_parent(), "boss_fireball", global_position + Vector2(0, -_body_size.y * 0.7), v + Vector2(randf_range(-80, 80), 0), 18.0, "enemy", {"gravity": 1100.0, "life": 2.5, "scale": 0.7, "through_walls": true})
		AudioManager.play_sfx("fireball", 0.1)
		await _wait(0.35)


func _p_flame_wave() -> void:
	play("jump")
	velocity.y = -700.0
	await _wait(0.2)
	while not dead and not is_on_floor():
		await get_tree().physics_frame
	if dead:
		return
	for dir in [-1.0, 1.0]:
		Projectile.spawn(get_parent(), "flame_wave", global_position + Vector2(dir * 60, -40), Vector2(dir * 520.0, 0), 20.0, "enemy", {"life": 2.6, "through_walls": true, "scale": 1.3})
	Events.camera_shake.emit(8.0, 0.25)
	AudioManager.play_sfx("fire", 0.0)
	await _wait(0.6)


func _land_shockwave(color: Color) -> void:
	Events.camera_shake.emit(12.0, 0.3)
	AudioManager.play_sfx("boss_stomp", 0.05)
	Haptics.heavy()
	Effects.dust(get_parent(), global_position, 14)
	Effects.flash(get_parent(), global_position + Vector2(0, -20), "circle_02", Color(color, 0.8), 0.4, 3.0, 0.35)
	for dir in [-1.0, 1.0]:
		Projectile.spawn(get_parent(), "flame_wave", global_position + Vector2(dir * (_body_size.x * 0.5 + 20), -36), Vector2(dir * 600.0, 0), 18.0, "enemy", {"life": 1.6, "through_walls": true, "color": color})


# ------------------------------------------------------------- helpers
func _telegraph(time: float) -> void:
	_warn.visible = true
	_warn.scale = Vector2(0.4, 0.4)
	var t := create_tween()
	t.tween_property(_warn, "scale", Vector2(1.1, 1.1), 0.12).set_trans(Tween.TRANS_BACK)
	fx_mat.set_shader_parameter("flash_color", Color(1, 0.15, 0.1))
	var flash := create_tween().set_loops(int(time / 0.16) + 1)
	flash.tween_method(func(v): fx_mat.set_shader_parameter("flash_amount", v), 0.0, 0.55, 0.08)
	flash.tween_method(func(v): fx_mat.set_shader_parameter("flash_amount", v), 0.55, 0.0, 0.08)
	AudioManager.play_sfx("alert", 0.0, -4.0)
	await _wait(time)
	flash.kill()
	if is_instance_valid(fx_mat):
		fx_mat.set_shader_parameter("flash_amount", 0.0)
	_warn.visible = false


func _ground_marker(pos: Vector2, time: float) -> void:
	var m := Sprite2D.new()
	m.texture = SpriteLib.tex("res://assets/effects/circle_05.png")
	m.material = Effects.add_material()
	m.modulate = Color(1, 0.2, 0.15, 0.8)
	m.scale = Vector2(0.9, 0.25)
	get_parent().add_child(m)
	m.global_position = pos + Vector2(0, -6)
	var t := m.create_tween()
	t.tween_property(m, "scale", Vector2(1.3, 0.35), time)
	t.parallel().tween_property(m, "modulate:a", 0.25, time)
	t.tween_callback(m.queue_free)


func _wait(t: float) -> void:
	await get_tree().create_timer(t, false).timeout


func _face_player() -> void:
	if player:
		facing = signf(player.global_position.x - global_position.x)
		if facing == 0:
			facing = -1


func play(anim: String) -> void:
	if sprite.sprite_frames.has_animation(anim):
		if sprite.animation != anim or not sprite.is_playing():
			sprite.play(anim)


func _afterimage() -> void:
	if int(SaveManager.setting("quality")) == 0:
		return
	var g := Sprite2D.new()
	g.texture = sprite.sprite_frames.get_frame_texture(sprite.animation, sprite.frame)
	g.flip_h = sprite.flip_h
	g.scale = sprite.scale
	g.material = fx_mat
	g.modulate = Color(1, 0.3, 0.3, 0.4)
	get_parent().add_child(g)
	g.global_position = global_position + sprite.offset * sprite.scale
	var t := g.create_tween()
	t.tween_property(g, "modulate:a", 0.0, 0.25)
	t.tween_callback(g.queue_free)


# -------------------------------------------------------------- damage
func take_damage(amount: float, _from: Vector2, _knock: float, crit: bool) -> void:
	if dead or not active:
		return
	hp = max(0.0, hp - amount)
	Events.boss_health_changed.emit(hp, max_hp)
	Effects.damage_number(get_parent(), global_position + Vector2(randf_range(-30, 30), -_body_size.y - 10), amount, crit)
	Effects.hit_spark(get_parent(), global_position + Vector2(randf_range(-20, 20), -_body_size.y * 0.5), Color(1, 0.85, 0.5), crit)
	AudioManager.play_sfx("boss_hurt", 0.1, -6.0)
	fx_mat.set_shader_parameter("flash_color", Color.WHITE)
	fx_mat.set_shader_parameter("flash_amount", 0.8)
	var t := create_tween()
	t.tween_method(_set_flash, 0.8, 0.0, 0.15)
	if phase == 1 and hp <= max_hp * 0.5:
		phase = 2
		Events.toast.emit("%s IS ENRAGED!" % cfg.name, Color(1, 0.35, 0.3))
		Events.camera_shake.emit(10.0, 0.4)
		if _aura:
			_aura.amount = 28
	if hp <= 0.0:
		_die()


func _set_flash(v: float) -> void:
	if is_instance_valid(fx_mat):
		fx_mat.set_shader_parameter("flash_amount", v)


func stomped(by: Player) -> bool:
	if kind == "ninja" or dead:
		by.take_damage(contact_damage, global_position, 600.0, false)
		return false
	take_damage(28.0, global_position, 0.0, false)
	return true


func freeze(_t: float) -> void:
	pass


func burn(_t: float) -> void:
	take_damage(6.0, global_position, 0.0, false)


func _die() -> void:
	dead = true
	active = false
	dangerous = false
	velocity = Vector2.ZERO
	set_collision_layer_value(3, false)
	_contact.monitoring = false
	Engine.time_scale = 0.35
	Events.camera_shake.emit(16.0, 0.6)
	Haptics.heavy()
	AudioManager.play_sfx("explosion", 0.0)
	if kind == "ninja":
		sprite.play("dead")
	else:
		sprite.play("hurt")
	for i in 5:
		var pos := global_position + Vector2(randf_range(-_body_size.x * 0.5, _body_size.x * 0.5), -randf_range(0, _body_size.y))
		get_tree().create_timer(0.08 * i, true, false, true).timeout.connect(func(): Effects.explosion(get_parent(), pos, 1.2))
	await get_tree().create_timer(0.6, true, false, true).timeout
	Engine.time_scale = 1.0
	var t := create_tween()
	t.tween_method(func(v): fx_mat.set_shader_parameter("dissolve", v), 0.0, 1.0, 1.0)
	await t.finished
	defeated.emit(self)
	queue_free()
