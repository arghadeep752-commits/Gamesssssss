class_name LevelProps
extends RefCounted
## Small interactive props built from the Kenney platformer pack sprites.

const PROPS := "res://assets/environments/props/"


class Spring:
	extends Area2D
	var power := 1650.0
	var _sprite: Sprite2D

	func _init() -> void:
		collision_layer = 0
		collision_mask = 2
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(56, 24)
		cs.shape = r
		cs.position = Vector2(0, 14)
		add_child(cs)
		_sprite = Sprite2D.new()
		_sprite.texture = SpriteLib.tex(PROPS + "spring.png")
		add_child(_sprite)

	func _physics_process(_d: float) -> void:
		for b in get_overlapping_bodies():
			if b.is_in_group("player") and b.velocity.y >= 0.0:
				b.spring_launch(power)
				_sprite.texture = SpriteLib.tex(PROPS + "spring_out.png")
				AudioManager.play_sfx("bounce", 0.05)
				get_tree().create_timer(0.35).timeout.connect(func(): _sprite.texture = SpriteLib.tex(PROPS + "spring.png"))


class Saw:
	extends Area2D
	var travel := 128.0
	var speed := 1.4
	var damage := 22.0
	var _origin := Vector2.ZERO
	var _t := 0.0
	var _sprite: Sprite2D

	func _init() -> void:
		collision_layer = 64
		collision_mask = 2
		var cs := CollisionShape2D.new()
		var c := CircleShape2D.new()
		c.radius = 28
		cs.shape = c
		add_child(cs)
		_sprite = Sprite2D.new()
		_sprite.texture = SpriteLib.tex(PROPS + "saw.png")
		add_child(_sprite)

	func _ready() -> void:
		_origin = position
		_t = randf() * TAU

	func _physics_process(delta: float) -> void:
		_t += delta * speed
		position.x = _origin.x + sin(_t) * travel
		_sprite.rotation += delta * 14.0
		for b in get_overlapping_bodies():
			if b.is_in_group("player"):
				b.take_damage(damage, global_position, 520.0, false)


class Crusher:
	extends AnimatableBody2D
	## Heavy weight that hangs, shakes, slams down and slowly rises.
	var drop := 192.0
	var damage := 40.0
	var _origin := Vector2.ZERO
	var _state := 0
	var _timer := 1.5
	var _vel := 0.0
	var _hit: Area2D
	var _sprite: Sprite2D

	func _init() -> void:
		collision_layer = 1
		collision_mask = 0
		sync_to_physics = false
		_sprite = Sprite2D.new()
		_sprite.texture = SpriteLib.tex(PROPS + "weight.png")
		_sprite.scale = Vector2(1.4, 1.4)
		add_child(_sprite)
		var chain := Sprite2D.new()
		chain.texture = SpriteLib.tex(PROPS + "chain.png")
		chain.position = Vector2(0, -64)
		chain.show_behind_parent = true
		add_child(chain)
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(80, 70)
		cs.shape = r
		add_child(cs)
		_hit = Area2D.new()
		_hit.collision_layer = 0
		_hit.collision_mask = 2
		var hs := CollisionShape2D.new()
		var hr := RectangleShape2D.new()
		hr.size = Vector2(74, 20)
		hs.shape = hr
		hs.position = Vector2(0, 42)
		_hit.add_child(hs)
		add_child(_hit)

	func _ready() -> void:
		_origin = position
		_timer = 0.8 + randf() * 1.6

	func _physics_process(delta: float) -> void:
		match _state:
			0:
				_timer -= delta
				if _timer < 0.45:
					_sprite.position.x = randf_range(-2.5, 2.5)
				if _timer <= 0:
					_state = 1
					_vel = 0.0
					_sprite.position.x = 0
			1:
				_vel += 3600 * delta
				position.y += _vel * delta
				for b in _hit.get_overlapping_bodies():
					if b.is_in_group("player"):
						b.take_damage(damage, global_position, 300.0, false)
				if position.y >= _origin.y + drop:
					position.y = _origin.y + drop
					_state = 2
					_timer = 0.6
					AudioManager.play_sfx("boss_stomp", 0.1, -6.0)
					Events.camera_shake.emit(6.0, 0.2)
			2:
				_timer -= delta
				if _timer <= 0:
					_state = 3
			3:
				position.y -= 140 * delta
				if position.y <= _origin.y:
					position.y = _origin.y
					_state = 0
					_timer = 1.6 + randf() * 0.8


class Ladder:
	extends Area2D
	func _init() -> void:
		add_to_group("ladder")
		collision_layer = 128
		collision_mask = 0
		monitoring = false


class HintSign:
	extends Area2D
	var text := ""
	var _label: Label
	var _shown := false

	func _init() -> void:
		collision_layer = 0
		collision_mask = 2
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(260, 200)
		cs.shape = r
		cs.position = Vector2(0, -60)
		add_child(cs)
		var s := Sprite2D.new()
		s.texture = SpriteLib.tex(PROPS + "sign.png")
		add_child(s)

	func _ready() -> void:
		_label = UITheme.make_label(text, 26, Color(1, 0.95, 0.75), true)
		_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_label.size = Vector2(360, 120)
		_label.position = Vector2(-180, -230)
		_label.modulate.a = 0.0
		_label.z_index = 20
		add_child(_label)
		body_entered.connect(func(b):
			if b.is_in_group("player"):
				create_tween().tween_property(_label, "modulate:a", 1.0, 0.25))
		body_exited.connect(func(b):
			if b.is_in_group("player"):
				create_tween().tween_property(_label, "modulate:a", 0.0, 0.4))
