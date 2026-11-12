class_name FallingPlatform
extends AnimatableBody2D
## Plank that shakes and drops shortly after the player stands on it, then respawns.

var _origin := Vector2.ZERO
var _state := 0   # 0 idle, 1 shaking, 2 falling, 3 gone
var _timer := 0.0
var _vel := 0.0
var _sensor: Area2D
var _sprite: Sprite2D


static func create(tex: Texture2D) -> FallingPlatform:
	var f := FallingPlatform.new()
	f.collision_layer = 1
	f.collision_mask = 0
	f.sync_to_physics = false
	f._sprite = Sprite2D.new()
	f._sprite.texture = tex
	f.add_child(f._sprite)
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(64, 30)
	cs.shape = r
	cs.position = Vector2(0, -12)
	cs.one_way_collision = true
	f.add_child(cs)
	f._sensor = Area2D.new()
	f._sensor.collision_layer = 0
	f._sensor.collision_mask = 2
	var ss := CollisionShape2D.new()
	var sr := RectangleShape2D.new()
	sr.size = Vector2(60, 12)
	ss.shape = sr
	ss.position = Vector2(0, -34)
	f._sensor.add_child(ss)
	f.add_child(f._sensor)
	return f


func _ready() -> void:
	_origin = position
	_sensor.body_entered.connect(func(b):
		if _state == 0 and b.is_in_group("player"):
			_state = 1
			_timer = 0.45)


func _physics_process(delta: float) -> void:
	match _state:
		1:
			_timer -= delta
			_sprite.position.x = randf_range(-3, 3)
			if _timer <= 0:
				_state = 2
				_vel = 0.0
				_sprite.position.x = 0
		2:
			_vel += 1800 * delta
			position.y += _vel * delta
			if position.y > _origin.y + 900:
				_state = 3
				_timer = 2.8
				visible = false
				for c in get_children():
					if c is CollisionShape2D:
						c.set_deferred("disabled", true)
		3:
			_timer -= delta
			if _timer <= 0:
				position = _origin
				visible = true
				modulate.a = 0.0
				create_tween().tween_property(self, "modulate:a", 1.0, 0.3)
				for c in get_children():
					if c is CollisionShape2D:
						c.set_deferred("disabled", false)
				_state = 0
