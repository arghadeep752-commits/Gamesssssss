class_name Player
extends CharacterBody2D
## The ninja. Movement + combat live here; behaviour flow is driven by PlayerStateMachine.

signal died

const GRAVITY := 2200.0
const MAX_FALL := 1350.0
const ACCEL := 2800.0
const AIR_ACCEL := 2100.0
const FRICTION := 3200.0
const COYOTE_TIME := 0.1
const JUMP_BUFFER := 0.13
const GLIDE_FALL := 165.0
const CLIMB_SPEED := 240.0
const SPECIAL_COST := 60.0
const MAX_ENERGY := 100.0
const BODY_H := 92.0

var data: CharacterData
var weapon: WeaponData
var weapon_level := 1
var max_health := 100.0
var health := 100.0
var energy := 0.0
var facing := 1.0
var invuln := 0.0
var coyote := 0.0
var jump_buffer := 0.0
var air_jumps_used := 0
var permanent_double_jump := false
var powerups := {}
var attack_cd := 0.0
var ability_cd := 0.0
var climbing := false
var controls_enabled := true
var spring_boost := false
var ice := false
var safe_pos := Vector2.ZERO
var level_bottom := 1408.0
var frozen_input := 0.0

var sprite: AnimatedSprite2D
var fx_mat: ShaderMaterial
var machine: PlayerStateMachine
var _ladder_area: Area2D
var _stomp_area: Area2D
var _shield: Sprite2D
var _aura: CPUParticles2D
var _safe_timer := 0.0
var _after_t := 0.0
var _blink_t := 0.0
var _respawning := false


func _ready() -> void:
	add_to_group("player")
	collision_layer = 2
	collision_mask = 1 | 128
	floor_snap_length = 10.0
	floor_max_angle = deg_to_rad(50)
	var cs := CollisionShape2D.new()
	var cap := CapsuleShape2D.new()
	cap.radius = 22.0
	cap.height = BODY_H
	cs.shape = cap
	cs.position = Vector2(0, -BODY_H / 2.0)
	add_child(cs)
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = SpriteLib.ninja_frames()
	sprite.centered = true
	var cell_h := SpriteLib.ninja_cell_height()
	sprite.offset = Vector2(0, -(cell_h / 2.0 - SpriteLib.ninja_foot_margin()))
	add_child(sprite)
	sprite.animation_finished.connect(func(): machine.current.on_animation_finished())
	sprite.frame_changed.connect(func(): machine.current.on_frame_changed(sprite.frame))
	_ladder_area = _make_sensor(Vector2(20, 60), Vector2(0, -40), 32)
	_stomp_area = _make_sensor(Vector2(40, 16), Vector2(0, 2), 4)
	_shield = Sprite2D.new()
	_shield.texture = SpriteLib.tex("res://assets/effects/circle_05.png")
	_shield.material = Effects.add_material()
	_shield.modulate = Color(0.4, 0.75, 1.0, 0.7)
	_shield.scale = Vector2(1.3, 1.3)
	_shield.position = Vector2(0, -48)
	_shield.visible = false
	add_child(_shield)
	machine = PlayerStateMachine.new(self)
	machine.change("idle")


func _make_sensor(size: Vector2, pos: Vector2, mask: int) -> Area2D:
	var a := Area2D.new()
	a.collision_layer = 0
	a.collision_mask = mask
	a.monitorable = false
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = size
	cs.shape = r
	cs.position = pos
	a.add_child(cs)
	add_child(a)
	return a


## Configure from the selected character, weapon and upgrades.
func setup(p_data: CharacterData, p_weapon: WeaponData, p_weapon_level: int, bonus_hp: float, double_jump: bool) -> void:
	data = p_data
	weapon = p_weapon
	weapon_level = p_weapon_level
	max_health = data.max_health + bonus_hp
	health = max_health
	permanent_double_jump = double_jump
	fx_mat = SpriteLib.material_for_character(data)
	sprite.material = fx_mat
	_setup_aura()
	_emit_stats()


func _setup_aura() -> void:
	if _aura:
		_aura.queue_free()
		_aura = null
	if data.aura == "" or int(SaveManager.setting("quality")) == 0:
		return
	_aura = CPUParticles2D.new()
	_aura.amount = 10
	_aura.lifetime = 0.8
	_aura.position = Vector2(0, -50)
	_aura.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_aura.emission_rect_extents = Vector2(22, 40)
	_aura.direction = Vector2(0, -1)
	_aura.spread = 25
	_aura.gravity = Vector2(0, -60)
	_aura.initial_velocity_min = 10
	_aura.initial_velocity_max = 40
	_aura.scale_amount_min = 0.05
	_aura.scale_amount_max = 0.11
	_aura.local_coords = false
	_aura.material = Effects.add_material()
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0.9))
	ramp.set_color(1, Color(1, 1, 1, 0))
	_aura.color_ramp = ramp
	match data.aura:
		"fire":
			_aura.texture = SpriteLib.tex("res://assets/effects/flame_01.png")
			_aura.color = Color(1, 0.5, 0.15)
		"ice":
			_aura.texture = SpriteLib.tex("res://assets/effects/star_04.png")
			_aura.color = Color(0.6, 0.9, 1)
		"shadow":
			_aura.texture = SpriteLib.tex("res://assets/effects/smoke_04.png")
			_aura.color = Color(0.45, 0.25, 0.75, 0.8)
			_aura.scale_amount_max = 0.18
		"gold":
			_aura.texture = SpriteLib.tex("res://assets/effects/spark_04.png")
			_aura.color = Color(1, 0.85, 0.35)
	add_child(_aura)
	move_child(_aura, 0)


# --------------------------------------------------------------- loop
func _physics_process(delta: float) -> void:
	if Input.is_action_just_pressed("jump") and controls_enabled:
		jump_buffer = JUMP_BUFFER
	else:
		jump_buffer = max(0.0, jump_buffer - delta)
	attack_cd = max(0.0, attack_cd - delta)
	if ability_cd > 0.0:
		ability_cd = max(0.0, ability_cd - delta)
		Events.ability_cooldown_changed.emit(ability_cd / max(0.01, weapon.ability_cooldown))
	_tick_powerups(delta)
	if invuln > 0.0:
		invuln -= delta
		_blink_t += delta
		sprite.visible = fmod(_blink_t, 0.12) < 0.07 or has_powerup("shield")
		if invuln <= 0.0:
			sprite.visible = true
	machine.physics_update(delta)
	if is_on_floor():
		air_jumps_used = 0
		spring_boost = false
	_update_facing()
	_track_safe_spot(delta)
	if global_position.y > level_bottom + 120.0 and not _respawning and machine.current_name != "death":
		_pit_fall()
	if (has_powerup("speed_boost") or machine.current_name == "special_attack") and absf(velocity.x) > 200.0:
		_after_t -= delta
		if _after_t <= 0.0:
			_after_t = 0.06
			spawn_afterimage()


func _update_facing() -> void:
	if not controls_enabled or machine.current_name in ["attack", "special_attack", "hurt", "death", "climb"]:
		sprite.flip_h = facing < 0
		return
	var x := input_x()
	if absf(x) > 0.1:
		facing = signf(x)
	sprite.flip_h = facing < 0


func _track_safe_spot(delta: float) -> void:
	_safe_timer -= delta
	if _safe_timer > 0.0 or not is_on_floor():
		return
	_safe_timer = 0.2
	var floor_body := get_last_slide_collision()
	if floor_body and (floor_body.get_collider() is AnimatableBody2D):
		return
	var space := get_world_2d().direct_space_state
	var ok := true
	for dx in [-40.0, 40.0]:
		var q := PhysicsRayQueryParameters2D.create(global_position + Vector2(dx, -10), global_position + Vector2(dx, 30), 1 | 128)
		if space.intersect_ray(q).is_empty():
			ok = false
	if ok:
		safe_pos = global_position


# -------------------------------------------------------------- input
func input_x() -> float:
	if not controls_enabled or frozen_input > 0.0:
		return 0.0
	return Input.get_axis("move_left", "move_right")


func consume_jump(air := false) -> bool:
	if not controls_enabled or jump_buffer <= 0.0:
		return false
	if air:
		if not has_air_jump():
			return false
	elif not (is_on_floor() or coyote > 0.0 or climbing):
		return false
	jump_buffer = 0.0
	if Input.is_action_pressed("move_down") and is_on_floor() and _standing_on_oneway():
		_drop_through()
		return false
	return true


func has_air_jump() -> bool:
	return (permanent_double_jump or has_powerup("double_jump")) and air_jumps_used < 1


func wants_attack() -> bool:
	return controls_enabled and Input.is_action_just_pressed("attack")


func wants_special() -> bool:
	return controls_enabled and Input.is_action_just_pressed("special")


func wants_ability() -> bool:
	return controls_enabled and Input.is_action_just_pressed("ability")


func can_use_special() -> bool:
	if energy < SPECIAL_COST:
		Events.toast.emit("Not enough energy!", Color(0.8, 0.7, 1))
		return false
	return true


func can_use_ability() -> bool:
	return ability_cd <= 0.0


func near_ladder() -> bool:
	return current_ladder() != null


func current_ladder() -> Area2D:
	for a in _ladder_area.get_overlapping_areas():
		if a.is_in_group("ladder"):
			return a
	return null


func _standing_on_oneway() -> bool:
	var space := get_world_2d().direct_space_state
	var q := PhysicsRayQueryParameters2D.create(global_position + Vector2(0, -4), global_position + Vector2(0, 20), 1)
	return space.intersect_ray(q).is_empty()


func _drop_through() -> void:
	set_collision_mask_value(8, false)
	position.y += 6
	get_tree().create_timer(0.28).timeout.connect(func(): set_collision_mask_value(8, true))


# ----------------------------------------------------------- movement
func apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity.y = min(velocity.y + GRAVITY * delta, MAX_FALL)


func move_speed() -> float:
	var s := data.move_speed if data else 340.0
	if has_powerup("speed_boost"):
		s *= GameData.powerup("speed_boost").magnitude
	return s


func jump_velocity() -> float:
	return data.jump_velocity if data else 960.0


func move_horizontal(delta: float, dir: float) -> void:
	var target := dir * move_speed()
	var accel := ACCEL if is_on_floor() else AIR_ACCEL
	if ice and is_on_floor():
		accel *= 0.35
	if absf(dir) < 0.05:
		var fr := FRICTION if is_on_floor() else AIR_ACCEL * 0.5
		if ice and is_on_floor():
			fr *= 0.18
		velocity.x = move_toward(velocity.x, 0.0, fr * delta)
	else:
		velocity.x = move_toward(velocity.x, target, accel * delta)


func land(peak_speed: float) -> void:
	if peak_speed > 500.0:
		Effects.dust(get_parent(), global_position, 8 if peak_speed > 900.0 else 5)
		AudioManager.play_sfx("land", 0.1, -6.0)
		if peak_speed > 1100.0:
			Events.camera_shake.emit(3.0, 0.12)
	var t := create_tween()
	sprite.scale = Vector2(1.12, 0.88)
	t.tween_property(sprite, "scale", Vector2.ONE, 0.14)


func bump_head() -> void:
	var space := get_world_2d().direct_space_state
	var q := PhysicsShapeQueryParameters2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(30, 14)
	q.shape = r
	q.transform = Transform2D(0, global_position + Vector2(0, -BODY_H - 16))
	q.collision_mask = 1
	for hit in space.intersect_shape(q, 4):
		var c = hit.collider
		if c is Breakable and c.kind in ["coin_block", "crate"]:
			c.head_bump()


func spring_launch(power: float) -> void:
	spring_boost = true
	air_jumps_used = 0
	machine.change("jump", {"power": power, "spring": true})


func play_anim(name: String, restart := false) -> void:
	if restart or sprite.animation != name:
		sprite.play(name)
		if restart:
			sprite.frame = 0
			sprite.play(name)


# ------------------------------------------------------------- combat
func weapon_damage() -> float:
	var dmg := weapon.damage_at(weapon_level) * data.damage_multiplier
	return dmg


func _roll_crit() -> bool:
	return has_powerup("critical_strike") or randf() < 0.12


func _crit_mult() -> float:
	return GameData.powerup("critical_strike").magnitude if has_powerup("critical_strike") else 1.8


func perform_weapon_hit(combo: int) -> void:
	if weapon.kind == "ranged":
		var crit := _roll_crit()
		var dmg := weapon_damage() * (_crit_mult() if crit else 1.0)
		var origin := global_position + Vector2(facing * 40.0, -62.0)
		Projectile.spawn(get_parent(), weapon.projectile, origin, Vector2(facing * weapon.projectile_speed, 0), dmg, "player", {"crit": crit, "life": 1.3})
		return
	var reach := weapon.reach * (1.15 if combo == 2 else 1.0)
	var center := global_position + Vector2(facing * (reach.x / 2.0 + 6.0), -52.0)
	Effects.slash(get_parent(), center + Vector2(facing * 6, -4), facing, weapon.effect_color, reach.x / 110.0)
	if weapon.id == "dragon_blade":
		Effects.flash(get_parent(), center, "flame_05", Color(1, 0.5, 0.15, 0.8), 0.3, 0.6, 0.25)
	for i in weapon.hits_per_attack:
		var hits := _melee_query(center, reach)
		for body in hits:
			var crit := _roll_crit()
			var dmg := weapon_damage() * (_crit_mult() if crit else 1.0)
			if combo == 2:
				dmg *= 1.25
			_deal(body, dmg, crit, 340.0)
			if weapon.id == "dragon_blade" and body.has_method("burn"):
				body.burn(2.0)


func _melee_query(center: Vector2, size: Vector2) -> Array:
	var q := PhysicsShapeQueryParameters2D.new()
	var r := RectangleShape2D.new()
	r.size = size
	q.shape = r
	q.transform = Transform2D(0, center)
	q.collision_mask = 1 | 4 | 32
	q.collide_with_areas = false
	q.exclude = [get_rid()]
	var out := []
	for hit in get_world_2d().direct_space_state.intersect_shape(q, 24):
		var c = hit.collider
		if c != self and c.has_method("take_damage") and not out.has(c):
			out.append(c)
	return out


func _deal(body: Node, dmg: float, crit: bool, knock: float) -> void:
	body.take_damage(dmg, global_position, knock, crit)
	if body.is_in_group("enemy"):
		add_energy(8.0)
		Events.hit_stop.emit(0.05 if not crit else 0.08)
		Haptics.light()
		AudioManager.play_sfx("sword_hit" if weapon.kind == "melee" else "hit", 0.1, -3.0)


func area_hit(radius: float, dmg: float, hits: Dictionary, interval: float) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	var center := global_position + Vector2(0, -50)
	for body in _melee_query(center, Vector2(radius * 2.0, radius * 1.4)):
		var id: int = body.get_instance_id()
		if hits.get(id, -10.0) + interval > now:
			continue
		hits[id] = now
		_deal(body, dmg, false, 300.0)
		Effects.slash(get_parent(), body.global_position + Vector2(0, -30), randf_range(-1, 1), Color(0.8, 0.95, 1), 0.8)


func dash_hits(hits: Dictionary, dmg: float) -> void:
	var center := global_position + Vector2(facing * 30.0, -50.0)
	for body in _melee_query(center, Vector2(110, 90)):
		var id: int = body.get_instance_id()
		if hits.has(id):
			continue
		hits[id] = true
		_deal(body, dmg * data.damage_multiplier, _roll_crit(), 420.0)
		Effects.slash(get_parent(), body.global_position + Vector2(0, -30), facing, Color(0.75, 0.6, 1.0), 1.0)


func do_special_effect(id: String) -> void:
	var p := get_parent()
	var base := weapon_damage()
	match id:
		"kunai_barrage":
			for i in 5:
				var ang := deg_to_rad(-20.0 + i * 10.0)
				var v := Vector2(facing * 1000.0, 0).rotated(ang * facing)
				Projectile.spawn(p, "kunai", global_position + Vector2(facing * 30, -60), v, base * 0.9 + 10.0, "player", {"pierce": true, "life": 1.0})
		"rising_slash":
			Effects.flash(p, global_position + Vector2(0, -60), "slash_04", Color(1, 0.85, 0.35), 1.2, 3.0, 0.3)
			Events.camera_shake.emit(7.0, 0.25)
			for body in _melee_query(global_position + Vector2(0, -70), Vector2(320, 220)):
				_deal(body, base * 2.2 + 20.0, true, 600.0)
		"flame_wave":
			for dir in [-1.0, 1.0]:
				Projectile.spawn(p, "flame_wave", global_position + Vector2(dir * 40, -36), Vector2(dir * 720.0, 0), base * 1.3 + 14.0, "player", {"pierce": true, "life": 0.9, "burn": true, "color": Color(1, 0.7, 0.4)})
			Events.camera_shake.emit(4.0, 0.2)
		"frost_nova":
			Effects.flash(p, global_position + Vector2(0, -50), "circle_02", Color(0.6, 0.9, 1, 0.9), 0.4, 4.5, 0.45)
			Effects.burst(p, global_position + Vector2(0, -50), "star_04", Color(0.7, 0.95, 1), 18, 600.0, 0.6, 0.12, 0.0)
			for body in _melee_query(global_position + Vector2(0, -50), Vector2(560, 360)):
				_deal(body, base * 1.4 + 10.0, false, 100.0)
				if body.has_method("freeze"):
					body.freeze(3.0)
			AudioManager.play_sfx("magic", 0.0)
		"fan_throw":
			for i in 3:
				var v := Vector2(facing * weapon.projectile_speed, 0).rotated(deg_to_rad(-12 + i * 12) * facing)
				Projectile.spawn(p, "shuriken", global_position + Vector2(facing * 30, -62), v, base * 1.1, "player", {"life": 1.2})
		"power_shot":
			Projectile.spawn(p, "arrow", global_position + Vector2(facing * 30, -62), Vector2(facing * 1700.0, 0), base * 2.5, "player", {"pierce": true, "life": 1.2, "scale": 1.5, "color": Color(1, 0.9, 0.6)})
			Effects.flash(p, global_position + Vector2(facing * 40, -62), "muzzle_02", Color(1, 0.9, 0.6), 0.3, 0.7, 0.18)
		"shadow_dash", "dash_slash", "whirlwind":
			pass


func add_energy(amount: float) -> void:
	energy = clampf(energy + amount, 0.0, MAX_ENERGY)
	Events.player_energy_changed.emit(energy, MAX_ENERGY)


func spend_special() -> void:
	energy = max(0.0, energy - SPECIAL_COST)
	Events.player_energy_changed.emit(energy, MAX_ENERGY)


func spawn_afterimage() -> void:
	if int(SaveManager.setting("quality")) == 0:
		return
	var ghost := Sprite2D.new()
	ghost.texture = sprite.sprite_frames.get_frame_texture(sprite.animation, sprite.frame)
	ghost.flip_h = sprite.flip_h
	ghost.global_position = sprite.global_position + sprite.offset
	ghost.modulate = Color(0.55, 0.45, 1.0, 0.45)
	ghost.material = fx_mat
	ghost.z_index = -1
	get_parent().add_child(ghost)
	ghost.global_position = global_position + sprite.offset
	var t := ghost.create_tween()
	t.tween_property(ghost, "modulate:a", 0.0, 0.25)
	t.tween_callback(ghost.queue_free)


func try_stomp() -> void:
	if velocity.y <= 60.0:
		return
	for body in _stomp_area.get_overlapping_bodies():
		if body.is_in_group("enemy") and body.has_method("stomped") and body.global_position.y > global_position.y + 4.0:
			if body.stomped(self):
				velocity.y = -720.0 if not Input.is_action_pressed("jump") else -980.0
				air_jumps_used = 0
				add_energy(10.0)
				machine.change("jump", {"power": -velocity.y, "spring": true})
				return


func take_damage(amount: float, from: Vector2, knock: float, _crit: bool) -> void:
	if invuln > 0.0 or machine.current_name in ["death", "victory"] or _respawning:
		return
	if has_powerup("shield"):
		Effects.flash(get_parent(), global_position + Vector2(0, -48), "circle_05", Color(0.5, 0.8, 1), 1.0, 1.8, 0.25)
		AudioManager.play_sfx("sword_hit", 0.1)
		invuln = 0.3
		return
	var dmg := amount * (1.0 - data.defense)
	health = max(0.0, health - dmg)
	invuln = 1.0
	_blink_t = 0.0
	_flash(Color(1, 0.3, 0.3))
	Effects.hit_spark(get_parent(), global_position + Vector2(0, -50), Color(1, 0.4, 0.4), true)
	AudioManager.play_sfx("hit", 0.08)
	Events.camera_shake.emit(6.0, 0.18)
	Haptics.medium()
	_emit_stats()
	if health <= 0.0:
		machine.change("death")
	elif machine.current_name != "special_attack":
		machine.change("hurt", {"from": from, "knock": knock})


func hazard_hit(zone: HazardZone) -> void:
	if zone.respawn:
		if _respawning or machine.current_name == "death":
			return
		_hazard_respawn(zone.damage)
	else:
		take_damage(zone.damage, zone.global_position + Vector2(0, 60), zone.knock, false)


func _pit_fall() -> void:
	_hazard_respawn(20.0)


func _hazard_respawn(dmg: float) -> void:
	_respawning = true
	health = max(0.0, health - dmg * (1.0 - data.defense))
	_emit_stats()
	AudioManager.play_sfx("water" if global_position.y > level_bottom else "hit", 0.0)
	Haptics.medium()
	if health <= 0.0:
		_respawning = false
		velocity = Vector2.ZERO
		machine.change("death")
		return
	controls_enabled = false
	var t := create_tween()
	t.tween_property(sprite, "modulate:a", 0.0, 0.15)
	t.tween_callback(func():
		global_position = safe_pos
		velocity = Vector2.ZERO
		machine.change("idle"))
	t.tween_property(sprite, "modulate:a", 1.0, 0.2)
	t.tween_callback(func():
		controls_enabled = true
		invuln = 1.2
		_respawning = false)


func respawn_at(pos: Vector2) -> void:
	global_position = pos
	safe_pos = pos
	velocity = Vector2.ZERO
	health = max_health
	visible = true
	sprite.visible = true
	sprite.modulate = Color.WHITE
	controls_enabled = true
	invuln = 1.5
	_respawning = false
	machine.change("idle")
	_emit_stats()


func heal(amount: float) -> void:
	health = min(max_health, health + amount)
	Effects.burst(get_parent(), global_position + Vector2(0, -50), "star_04", Color(0.5, 1, 0.5), 10, 220.0, 0.6, 0.1, -100.0)
	AudioManager.play_sfx("heal", 0.0)
	_emit_stats()


func _flash(color: Color) -> void:
	if fx_mat == null:
		return
	fx_mat.set_shader_parameter("flash_color", color)
	fx_mat.set_shader_parameter("flash_amount", 0.75)
	var t := create_tween()
	t.tween_method(func(v): fx_mat.set_shader_parameter("flash_amount", v), 0.75, 0.0, 0.22)


func _emit_stats() -> void:
	Events.player_health_changed.emit(health, max_health)
	Events.player_energy_changed.emit(energy, MAX_ENERGY)


# ------------------------------------------------------------ pickups
func collect(p: Pickup) -> void:
	match p.kind:
		"coin":
			AudioManager.play_sfx("coin", 0.08, -3.0)
			get_tree().call_group("game", "on_coin_collected", p.value)
		"gem":
			AudioManager.play_sfx("gem", 0.03)
			get_tree().call_group("game", "on_gem_collected", p.value)
			Haptics.light()
		"heart":
			heal(30.0)
		"powerup":
			apply_powerup(p.powerup_id)


func apply_powerup(id: String) -> void:
	var data_p: PowerupData = GameData.powerup(id)
	if data_p == null:
		return
	AudioManager.play_sfx("powerup", 0.0)
	Haptics.medium()
	Effects.flash(get_parent(), global_position + Vector2(0, -50), "light_01", Color(data_p.color, 0.9), 0.5, 2.5, 0.4)
	match id:
		"health_recovery":
			heal(data_p.magnitude)
		"energy_boost":
			add_energy(data_p.magnitude)
		_:
			powerups[id] = data_p.duration
			if id == "shield":
				_shield.visible = true
	Events.powerup_started.emit(id, data_p.duration)
	Events.toast.emit(data_p.display_name.to_upper() + "!", data_p.color)


func has_powerup(id: String) -> bool:
	return powerups.get(id, 0.0) > 0.0


func _tick_powerups(delta: float) -> void:
	for id in powerups.keys():
		powerups[id] -= delta
		if powerups[id] <= 0.0:
			powerups.erase(id)
			if id == "shield":
				_shield.visible = false
			Events.powerup_ended.emit(id)
	if _shield.visible:
		_shield.rotation += delta * 1.5
		_shield.modulate.a = 0.45 + sin(Time.get_ticks_msec() / 120.0) * 0.15


func celebrate() -> void:
	machine.change("victory")


func is_dead() -> bool:
	return machine.current_name == "death"
