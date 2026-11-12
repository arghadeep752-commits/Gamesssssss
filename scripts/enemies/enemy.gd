class_name Enemy
extends CharacterBody2D
## Data-driven enemy. Archetypes come from GameData.ENEMIES; behaviour is picked by key.

const GRAVITY := 2000.0
const WAKE_DISTANCE := 1300.0

var id := "slime"
var cfg := {}
var behavior := "walker"
var max_hp := 30.0
var hp := 30.0
var damage := 10.0
var speed := 60.0
var stompable := true
var coins := 2
var facing := -1.0
var difficulty := 1.0
var is_ninja := false
var dead := false

var sprite: AnimatedSprite2D
var fx_mat: ShaderMaterial
var player: Player
var home := Vector2.ZERO
var state := "patrol"
var timer := 0.0
var attack_timer := 0.0
var hurt_timer := 0.0
var frozen := 0.0
var burning := 0.0
var _burn_tick := 0.0
var _contact: Area2D
var _ice_overlay: Sprite2D
var _t := 0.0
var _hit_done := false


static func create(p_id: String, p_difficulty: float) -> Enemy:
	var e := Enemy.new()
	e.id = p_id
	e.difficulty = p_difficulty
	e.cfg = GameData.ENEMIES.get(p_id, GameData.ENEMIES["slime"])
	return e


func _ready() -> void:
	add_to_group("enemy")
	collision_layer = 4
	collision_mask = 1 | 128
	behavior = cfg.behavior
	max_hp = float(cfg.hp) * (0.85 + difficulty * 0.18)
	hp = max_hp
	damage = float(cfg.damage) * (0.9 + difficulty * 0.1)
	speed = float(cfg.speed)
	stompable = bool(cfg.stomp)
	coins = int(cfg.coins)
	is_ninja = cfg.sprite == "ninja"
	home = global_position
	facing = -1.0 if randf() < 0.5 else 1.0
	_t = randf() * 10.0
	sprite = AnimatedSprite2D.new()
	add_child(sprite)
	var body_size := Vector2(48, 44)
	if is_ninja:
		sprite.sprite_frames = SpriteLib.ninja_frames()
		var ch := SpriteLib.ninja_cell_height()
		sprite.offset = Vector2(0, -(ch / 2.0 - SpriteLib.ninja_foot_margin()))
		sprite.scale = Vector2(0.92, 0.92)
		fx_mat = SpriteLib.make_fx_material(cfg.get("cloth_hue", 0.0), cfg.get("cloth_sat", 0.0), cfg.get("cloth_val", 0.5), Color(0.75, 0.7, 0.75))
		body_size = Vector2(40, 86)
		sprite.play("idle")
	else:
		sprite.sprite_frames = SpriteLib.critter_frames(cfg.sprite)
		sprite.offset = Vector2(0, -32)
		fx_mat = SpriteLib.make_fx_material()
		sprite.play("move")
		if behavior in ["flyer", "chaser"]:
			body_size = Vector2(44, 36)
	sprite.material = fx_mat
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = body_size
	cs.shape = r
	cs.position = Vector2(0, -body_size.y / 2.0)
	add_child(cs)
	_contact = Area2D.new()
	_contact.collision_layer = 0
	_contact.collision_mask = 2
	_contact.monitorable = false
	var ccs := CollisionShape2D.new()
	var cr := RectangleShape2D.new()
	cr.size = body_size * 0.85
	ccs.shape = cr
	ccs.position = cs.position
	_contact.add_child(ccs)
	add_child(_contact)
	if behavior == "leaper":
		collision_mask = 0
		visible = false
		timer = 1.0 + randf() * 1.5
	if behavior == "chomper":
		collision_mask = 1


func _physics_process(delta: float) -> void:
	if dead:
		return
	if player == null or not is_instance_valid(player):
		player = get_tree().get_first_node_in_group("player")
		if player == null:
			return
	if global_position.distance_squared_to(player.global_position) > WAKE_DISTANCE * WAKE_DISTANCE and behavior != "leaper":
		return
	_t += delta
	_tick_status(delta)
	if frozen > 0.0:
		velocity.x = 0.0
		if behavior not in ["flyer", "chaser"]:
			velocity.y = min(velocity.y + GRAVITY * delta, 1200.0)
		move_and_slide()
		return
	if hurt_timer > 0.0:
		hurt_timer -= delta
		if behavior not in ["flyer", "chaser"]:
			velocity.y = min(velocity.y + GRAVITY * delta, 1200.0)
		velocity.x = move_toward(velocity.x, 0.0, 900.0 * delta)
		move_and_slide()
		return
	match behavior:
		"walker":
			_walker(delta)
		"hopper":
			_hopper(delta)
		"charger":
			_charger(delta)
		"flyer":
			_flyer(delta)
		"chaser":
			_chaser(delta)
		"jumper":
			_jumper(delta)
		"chomper":
			_chomper(delta)
		"leaper":
			_leaper(delta)
		"ninja":
			_ninja(delta, false)
		"thrower":
			_ninja(delta, true)
	sprite.flip_h = facing > 0.0 if not is_ninja else facing < 0.0
	_contact_damage()


# ------------------------------------------------------------ helpers
func _gravity(delta: float) -> void:
	velocity.y = min(velocity.y + GRAVITY * delta, 1200.0)


func _edge_ahead() -> bool:
	var space := get_world_2d().direct_space_state
	var from := global_position + Vector2(facing * 30.0, -8.0)
	var q := PhysicsRayQueryParameters2D.create(from, from + Vector2(0, 50), 1 | 128)
	return space.intersect_ray(q).is_empty()


func _to_player() -> Vector2:
	return player.global_position - global_position


func _player_visible(dist: float, max_dy := 160.0) -> bool:
	var d := _to_player()
	return absf(d.x) < dist and absf(d.y) < max_dy and not player.is_dead()


func _patrol(delta: float, spd: float) -> void:
	_gravity(delta)
	if is_on_floor() and (is_on_wall() or _edge_ahead()):
		facing = -facing
	velocity.x = facing * spd
	move_and_slide()


func _contact_damage() -> void:
	for b in _contact.get_overlapping_bodies():
		if b is Player:
			var p: Player = b
			if stompable and p.velocity.y > 60.0 and p.global_position.y < global_position.y - 14.0:
				continue
			p.take_damage(damage, global_position, 480.0, false)


# --------------------------------------------------------- behaviours
func _walker(delta: float) -> void:
	_patrol(delta, speed * (1.0 + difficulty * 0.05))
	if cfg.get("shoots", false):
		attack_timer -= delta
		if attack_timer <= 0.0 and _player_visible(520.0, 120.0):
			attack_timer = 2.6
			var dir := signf(_to_player().x)
			Projectile.spawn(get_parent(), "fireball", global_position + Vector2(dir * 30, -30), Vector2(dir * 420.0, -260.0), damage * 0.8, "enemy", {"gravity": 900.0, "life": 2.0})
			AudioManager.play_sfx("fireball", 0.1, -6.0)


func _hopper(delta: float) -> void:
	_gravity(delta)
	timer -= delta
	if is_on_floor():
		velocity.x = move_toward(velocity.x, 0.0, 1400.0 * delta)
		sprite.play("move" if absf(velocity.x) > 10 else "idle")
		if timer <= 0.0:
			timer = 1.3 + randf() * 0.6
			if _player_visible(500.0, 220.0):
				facing = signf(_to_player().x)
			elif is_on_wall() or _edge_ahead():
				facing = -facing
			velocity = Vector2(facing * speed * 1.6, -620.0)
			sprite.play("jump")
	move_and_slide()


func _charger(delta: float) -> void:
	if state == "charge":
		timer -= delta
		_gravity(delta)
		velocity.x = facing * speed
		move_and_slide()
		if timer <= 0.0 or is_on_wall():
			state = "rest"
			timer = 0.8
		return
	if state == "rest":
		timer -= delta
		_gravity(delta)
		velocity.x = 0
		move_and_slide()
		if timer <= 0.0:
			state = "patrol"
		return
	_patrol(delta, speed * 0.3)
	if _player_visible(340.0, 70.0) and signf(_to_player().x) == facing:
		state = "charge"
		timer = 1.0
		sprite.speed_scale = 2.0


func _flyer(delta: float) -> void:
	if state == "dive":
		timer -= delta
		velocity = velocity.move_toward(Vector2.ZERO, 300.0 * delta)
		move_and_slide()
		if timer <= 0.0:
			state = "return"
		return
	if state == "return":
		var back := home - global_position
		velocity = back.normalized() * speed
		move_and_slide()
		if back.length() < 20.0:
			state = "patrol"
		return
	var target := home + Vector2(sin(_t * 0.9) * 150.0, sin(_t * 2.2) * 24.0)
	velocity = (target - global_position) * 3.0
	facing = signf(velocity.x) if absf(velocity.x) > 5 else facing
	move_and_slide()
	attack_timer -= delta
	if attack_timer <= 0.0 and _player_visible(260.0, 320.0) and _to_player().y > -20.0:
		attack_timer = 2.4
		state = "dive"
		timer = 0.9
		velocity = _to_player().normalized() * 420.0 + Vector2(0, -30)
		facing = signf(velocity.x)


func _chaser(delta: float) -> void:
	var to := _to_player() + Vector2(0, -50)
	if to.length() < 520.0 and not player.is_dead():
		velocity = velocity.move_toward(to.normalized() * speed, 400.0 * delta)
	else:
		velocity = velocity.move_toward((home - global_position).limit_length(speed), 300.0 * delta)
	velocity.y += sin(_t * 5.0) * 20.0
	if absf(velocity.x) > 5:
		facing = signf(velocity.x)
	move_and_slide()


func _jumper(delta: float) -> void:
	_gravity(delta)
	timer -= delta
	if is_on_floor():
		velocity.x = move_toward(velocity.x, 0.0, 2000.0 * delta)
		sprite.play("idle")
		if timer <= 0.0:
			timer = 1.4 + randf() * 0.8
			if _player_visible(460.0, 200.0):
				facing = signf(_to_player().x)
			elif _edge_ahead() or is_on_wall():
				facing = -facing
			velocity = Vector2(facing * speed, -760.0)
			sprite.play("jump")
	move_and_slide()


func _chomper(delta: float) -> void:
	_gravity(delta)
	move_and_slide()
	var near := _player_visible(140.0, 120.0)
	sprite.play("attack" if near else "idle")
	sprite.speed_scale = 2.0 if near else 1.0
	stompable = false


func _leaper(delta: float) -> void:
	if state == "patrol":
		timer -= delta
		if timer <= 0.0 and _player_visible(700.0, 600.0):
			state = "leap"
			visible = true
			velocity = Vector2(randf_range(-60, 60), -1250.0)
			AudioManager.play_sfx("water", 0.2, -10.0)
		return
	velocity.y += GRAVITY * 0.9 * delta
	position += velocity * delta
	sprite.rotation = velocity.angle() + PI / 2.0
	if velocity.y > 0.0 and global_position.y >= home.y:
		global_position = home
		state = "patrol"
		visible = false
		timer = 1.4 + randf() * 1.4


func _ninja(delta: float, thrower: bool) -> void:
	_gravity(delta)
	attack_timer -= delta
	var d := _to_player()
	var sees := _player_visible(480.0, 140.0)
	if state == "attack":
		velocity.x = move_toward(velocity.x, 0.0, 2000.0 * delta)
		move_and_slide()
		return
	if sees:
		facing = signf(d.x)
		if thrower:
			var want := 300.0
			if absf(d.x) < 90.0 and attack_timer <= 0.0:
				_start_attack("attack")
				return
			if attack_timer <= 0.0:
				_start_attack("throw")
				return
			var dir := signf(d.x) * (1.0 if absf(d.x) > want + 60 else (-1.0 if absf(d.x) < want - 60 else 0.0))
			velocity.x = move_toward(velocity.x, dir * speed, 1400.0 * delta)
		else:
			if absf(d.x) < 95.0 and attack_timer <= 0.0:
				_start_attack("attack")
				return
			velocity.x = move_toward(velocity.x, facing * speed * (1.0 + difficulty * 0.04), 1600.0 * delta)
			if is_on_floor() and is_on_wall():
				velocity.y = -760.0
		if is_on_floor() and _edge_ahead() and d.y > -40:
			velocity.x = 0.0
	else:
		if is_on_floor() and (is_on_wall() or _edge_ahead()):
			facing = -facing
		velocity.x = move_toward(velocity.x, facing * speed * 0.45, 1000.0 * delta)
	move_and_slide()
	if not is_on_floor():
		sprite.play("fall" if velocity.y > 0 else "jump")
	else:
		sprite.play("run" if absf(velocity.x) > 20.0 else "idle")


func _start_attack(anim: String) -> void:
	state = "attack"
	_hit_done = false
	attack_timer = (1.9 if anim == "throw" else 1.1) / (0.9 + difficulty * 0.08)
	sprite.play(anim)
	sprite.speed_scale = 1.0
	if not sprite.frame_changed.is_connected(_on_ninja_frame):
		sprite.frame_changed.connect(_on_ninja_frame)
		sprite.animation_finished.connect(_on_ninja_anim_done)
	fx_mat.set_shader_parameter("flash_color", Color(1, 0.2, 0.2))
	fx_mat.set_shader_parameter("flash_amount", 0.4)
	create_tween().tween_method(func(v): fx_mat.set_shader_parameter("flash_amount", v), 0.4, 0.0, 0.25)


func _on_ninja_frame() -> void:
	if state != "attack" or _hit_done or sprite.frame != 4:
		return
	_hit_done = true
	if sprite.animation == "throw":
		var dir := facing
		Projectile.spawn(get_parent(), "kunai", global_position + Vector2(dir * 30, -58), Vector2(dir * 640.0, 0), damage * 0.8, "enemy", {"life": 1.6})
		AudioManager.play_sfx("throw", 0.1, -6.0)
	else:
		Effects.slash(get_parent(), global_position + Vector2(facing * 50, -50), facing, Color(1, 0.6, 0.6, 0.8), 0.8)
		AudioManager.play_sfx("swing1", 0.15, -6.0)
		var d := _to_player()
		if absf(d.x) < 110.0 and absf(d.y) < 90.0 and signf(d.x) == facing:
			player.take_damage(damage, global_position, 520.0, false)


func _on_ninja_anim_done() -> void:
	if state == "attack":
		state = "chase"


# -------------------------------------------------------------- damage
func take_damage(amount: float, from: Vector2, knock: float, crit: bool) -> void:
	if dead:
		return
	hp -= amount
	Effects.damage_number(get_parent(), global_position + Vector2(0, -60 if not is_ninja else -100), amount, crit)
	Effects.hit_spark(get_parent(), global_position + Vector2(0, -30 if not is_ninja else -55), Color(1, 0.9, 0.6), crit)
	fx_mat.set_shader_parameter("flash_color", Color.WHITE)
	fx_mat.set_shader_parameter("flash_amount", 0.9)
	var t := create_tween()
	t.tween_method(_set_flash, 0.9, 0.0, 0.18)
	if hp <= 0.0:
		die()
		return
	if behavior not in ["chomper", "leaper"] and frozen <= 0.0:
		var dir := signf(global_position.x - from.x)
		velocity = Vector2(dir * knock * (0.7 if is_ninja else 0.9), -180.0 if behavior not in ["flyer", "chaser"] else 0.0)
		hurt_timer = 0.22
		if is_ninja:
			sprite.play("hurt")
			state = "chase"
		else:
			sprite.play("hurt")
			get_tree().create_timer(0.22).timeout.connect(_end_hurt)


func _set_flash(v: float) -> void:
	if fx_mat:
		fx_mat.set_shader_parameter("flash_amount", v)


func _end_hurt() -> void:
	if is_instance_valid(self) and not dead and not is_ninja:
		sprite.play("move")


func stomped(by: Player) -> bool:
	if dead:
		return false
	if not stompable:
		by.take_damage(damage, global_position, 520.0, false)
		return false
	AudioManager.play_sfx("bounce", 0.1)
	take_damage(max_hp * 0.7 + 18.0, global_position + Vector2(0, -60), 0.0, false)
	if not dead:
		sprite.scale = Vector2(1.3, 0.7)
		create_tween().tween_property(sprite, "scale", Vector2.ONE, 0.2)
	return true


func freeze(time: float) -> void:
	if dead:
		return
	frozen = max(frozen, time)
	sprite.speed_scale = 0.0
	sprite.modulate = Color(0.55, 0.85, 1.4)


func burn(time: float) -> void:
	burning = max(burning, time)


func _tick_status(delta: float) -> void:
	if frozen > 0.0:
		frozen -= delta
		if frozen <= 0.0:
			sprite.speed_scale = 1.0
			sprite.modulate = Color.WHITE
	if burning > 0.0:
		burning -= delta
		_burn_tick -= delta
		if _burn_tick <= 0.0:
			_burn_tick = 0.45
			Effects.flash(get_parent(), global_position + Vector2(randf_range(-15, 15), -40), "flame_01", Color(1, 0.5, 0.15, 0.9), 0.2, 0.5, 0.35)
			hp -= 4.0
			if hp <= 0.0:
				die()


func die() -> void:
	if dead:
		return
	dead = true
	set_collision_layer_value(3, false)
	_contact.monitoring = false
	Events.enemy_killed.emit(self)
	SaveManager.add_stat("enemies", 1)
	AudioManager.play_sfx("enemy_die", 0.1)
	get_tree().call_group("game", "spawn_coins", global_position + Vector2(0, -40), coins)
	Effects.burst(get_parent(), global_position + Vector2(0, -30), "smoke_04", Color(1, 1, 1, 0.8), 10, 240.0, 0.5, 0.25, -50.0)
	Effects.burst(get_parent(), global_position + Vector2(0, -30), "star_04", Color(1, 0.9, 0.5), 8, 380.0, 0.4, 0.1)
	var t := create_tween()
	if is_ninja:
		sprite.play("dead")
		t.tween_interval(0.7)
		t.tween_method(func(v): fx_mat.set_shader_parameter("dissolve", v), 0.0, 1.0, 0.5)
	else:
		sprite.play("hurt")
		t.tween_property(sprite, "scale", Vector2(1.3, 0.3), 0.15)
		t.tween_property(sprite, "modulate:a", 0.0, 0.25)
	t.tween_callback(queue_free)
