class_name Projectile
extends Area2D
## Pooled projectile used by the player (kunai, shuriken, arrows, fire) and enemies/bosses.

const W := "res://assets/weapons/"

var velocity := Vector2.ZERO
var damage := 10.0
var team := "player"
var pierce := false
var through_walls := false
var life := 2.0
var spin := 0.0
var grav := 0.0
var knock := 260.0
var crit := false
var freeze := 0.0
var burn := false
var kind := ""
var _hits := {}
var _sprite: AnimatedSprite2D
var _shape: CollisionShape2D
var _trail_t := 0.0


static func _factory() -> Projectile:
	var p := Projectile.new()
	p._sprite = AnimatedSprite2D.new()
	p.add_child(p._sprite)
	p._shape = CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 14
	p._shape.shape = c
	p.add_child(p._shape)
	p.monitorable = false
	p.body_entered.connect(p._on_body)
	return p


static func spawn(parent: Node, p_kind: String, pos: Vector2, vel: Vector2, p_damage: float, p_team: String, opts := {}) -> Projectile:
	var p: Projectile = Pool.take("proj", _factory)
	p.kind = p_kind
	p.velocity = vel
	p.damage = p_damage
	p.team = p_team
	p.pierce = opts.get("pierce", false)
	p.through_walls = opts.get("through_walls", false)
	p.life = opts.get("life", 1.6)
	p.grav = opts.get("gravity", 0.0)
	p.knock = opts.get("knock", 260.0)
	p.crit = opts.get("crit", false)
	p.freeze = opts.get("freeze", 0.0)
	p.burn = opts.get("burn", false)
	p.spin = 0.0
	p._hits.clear()
	p.collision_layer = 8 if p_team == "player" else 16
	p.collision_mask = (4 if p_team == "player" else 2) | (0 if p.through_walls else 1)
	p.monitoring = true
	p.modulate = opts.get("color", Color.WHITE)
	p.scale = Vector2.ONE * float(opts.get("scale", 1.0))
	p._setup_visual()
	parent.add_child(p)
	p.global_position = pos
	p.rotation = 0.0 if p.spin != 0.0 else vel.angle()
	return p


func _setup_visual() -> void:
	var sf: SpriteFrames
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_PARENT_NODE
	_sprite.material = null
	var radius := 14.0
	match kind:
		"kunai":
			sf = _single(W + "kunai.png")
			radius = 12.0
		"shuriken":
			sf = SpriteLib.strip_frames(W + "shuriken_sheet.png", 69, 20.0)
			spin = 22.0
			_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			radius = 20.0
		"arrow":
			sf = _single(W + "arrow.png")
			_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			radius = 10.0
		"big_kunai":
			sf = _single(W + "big_kunai.png")
			_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		"fireball":
			sf = SpriteLib.strip_frames(W + "fireball_sheet.png", 48, 14.0)
			_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			_sprite.material = Effects.add_material()
			radius = 18.0
		"icespike":
			sf = SpriteLib.strip_frames(W + "icespike_sheet.png", 48, 14.0)
			_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			radius = 14.0
		"boss_fireball":
			sf = _single("res://assets/bosses/fireball_big.png")
			spin = 8.0
			radius = 34.0
		"flame_wave":
			sf = _single("res://assets/effects/flame_03.png")
			_sprite.material = Effects.add_material()
			radius = 34.0
		"shadow_orb":
			sf = _single("res://assets/effects/magic_04.png")
			_sprite.material = Effects.add_material()
			spin = 6.0
			radius = 22.0
		_:
			sf = _single(W + "kunai.png")
	_sprite.sprite_frames = sf
	_sprite.play("default")
	_sprite.scale = Vector2(0.55, 0.55) if kind in ["flame_wave", "shadow_orb"] else Vector2.ONE
	(_shape.shape as CircleShape2D).radius = radius


func _single(path: String) -> SpriteFrames:
	var key := "single:" + path
	if not SpriteLib._cache.has(key):
		var sf := SpriteFrames.new()
		sf.add_frame("default", SpriteLib.tex(path))
		SpriteLib._cache[key] = sf
	return SpriteLib._cache[key]


func _physics_process(delta: float) -> void:
	life -= delta
	velocity.y += grav * delta
	position += velocity * delta
	if spin != 0.0:
		rotation += spin * delta * signf(velocity.x if velocity.x != 0 else 1.0)
	elif grav != 0.0:
		rotation = velocity.angle()
	if kind == "flame_wave" or kind == "fireball" or kind == "boss_fireball":
		_trail_t -= delta
		if _trail_t <= 0.0 and int(SaveManager.setting("quality")) >= 1:
			_trail_t = 0.06
			Effects.flash(get_parent(), global_position, "flame_01", Color(1, 0.55, 0.2, 0.7), 0.18, 0.05, 0.3, randf() * TAU)
	if life <= 0.0:
		_despawn(false)


func _on_body(body: Node) -> void:
	if not monitoring:
		return
	var target_group := "enemy" if team == "player" else "player"
	if body.is_in_group(target_group) or (team == "player" and body.is_in_group("breakable")):
		if _hits.has(body.get_instance_id()):
			return
		_hits[body.get_instance_id()] = true
		if body.has_method("take_damage"):
			body.take_damage(damage, global_position - velocity.normalized() * 30.0, knock, crit)
		if freeze > 0.0 and body.has_method("freeze"):
			body.freeze(freeze)
		if burn and body.has_method("burn"):
			body.burn(3.0)
		if not pierce:
			_despawn(true)
	elif not through_walls and not body.is_in_group("player") and not body.is_in_group("enemy"):
		_despawn(true)


func _despawn(impact: bool) -> void:
	if not monitoring:
		return
	set_deferred("monitoring", false)
	if impact and is_inside_tree():
		Effects.hit_spark(get_parent(), global_position, modulate if kind != "fireball" else Color(1, 0.6, 0.2))
	Pool.give_back.call_deferred(self)
