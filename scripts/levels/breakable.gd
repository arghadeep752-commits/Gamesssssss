class_name Breakable
extends StaticBody2D
## Things the player can slash open: crates, treasure chests, coin blocks, secret walls.

signal broken(node: Breakable, at: Vector2)

var kind := "crate"     # crate, chest, coin_block, secret
var hp := 1.0
var coins_inside := 0
var _sprite: Sprite2D
var _opened := false


static func create(p_kind: String, tex: Texture2D) -> Breakable:
	var b := Breakable.new()
	b.kind = p_kind
	b.add_to_group("breakable")
	b.collision_layer = 1
	b.collision_mask = 0
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(64, 64)
	cs.shape = r
	b.add_child(cs)
	b._sprite = Sprite2D.new()
	b._sprite.texture = tex
	b.add_child(b._sprite)
	match p_kind:
		"crate":
			b.hp = 1.0
		"chest":
			b.hp = 1.0
			r.size = Vector2(60, 48)
			cs.position = Vector2(0, 8)
			b.collision_layer = 32   # not solid for movement; slash or touch to open
			var sensor := Area2D.new()
			sensor.collision_layer = 0
			sensor.collision_mask = 2
			var ss := CollisionShape2D.new()
			var sr := RectangleShape2D.new()
			sr.size = Vector2(70, 60)
			ss.shape = sr
			sensor.add_child(ss)
			b.add_child(sensor)
			sensor.body_entered.connect(func(body):
				if body.is_in_group("player"):
					b.take_damage(1.0, body.global_position, 0.0, false))
		"coin_block":
			b.hp = 3.0
			b.coins_inside = 3
		"secret":
			b.hp = 2.0
	return b


func take_damage(amount: float, from: Vector2, _knock: float, _crit: bool) -> void:
	if _opened:
		return
	if kind == "coin_block":
		_bump()
		broken.emit(self, global_position + Vector2(0, -48))
		hp -= 1.0
		if hp <= 0:
			_opened = true
			_sprite.texture = SpriteLib.tex("res://assets/environments/props/block_coin_active.png")
		return
	hp -= 1.0 if amount > 0 else 0.0
	_bump()
	if hp > 0:
		return
	_opened = true
	broken.emit(self, global_position)
	if kind == "chest":
		AudioManager.play_sfx("chest_open", 0.0)
		_sprite.texture = SpriteLib.tex("res://assets/environments/props/chest_open.png")
		var t := create_tween()
		t.tween_property(self, "scale", Vector2(1.25, 1.25), 0.1)
		t.tween_property(self, "scale", Vector2(1.0, 1.0), 0.15)
		t.tween_interval(1.5)
		t.tween_property(self, "modulate:a", 0.0, 0.5)
		t.tween_callback(queue_free)
	else:
		AudioManager.play_sfx("impact", 0.1)
		Effects.debris(get_parent(), global_position, _sprite.texture, 6)
		queue_free()


func head_bump() -> void:
	take_damage(1.0, global_position + Vector2(0, 40), 0.0, false)


func _bump() -> void:
	var t := create_tween()
	t.tween_property(_sprite, "position:y", -10.0, 0.06)
	t.tween_property(_sprite, "position:y", 0.0, 0.1)
