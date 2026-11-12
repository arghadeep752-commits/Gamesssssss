class_name Pickup
extends Area2D
## Collectible: coin, gem, heart or power-up. Bobs and spins, flies to the HUD when taken.

var kind := "coin"          # coin, gem, heart, powerup
var value := 1
var powerup_id := ""
var sprite: Sprite2D
var _base_y := 0.0
var _t := 0.0
var _taken := false
var magnet_target: Node2D
var flying := false


static func create(p_kind: String, tex: Texture2D, p_value := 1, p_powerup := "") -> Pickup:
	var p := Pickup.new()
	p.kind = p_kind
	p.value = p_value
	p.powerup_id = p_powerup
	p.collision_layer = 32
	p.collision_mask = 2
	p.monitorable = false
	var shape := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 26.0 if p_kind == "coin" else 30.0
	shape.shape = c
	p.add_child(shape)
	p.sprite = Sprite2D.new()
	p.sprite.texture = tex
	if p_kind == "coin":
		p.sprite.scale = Vector2(0.75, 0.75)
	elif p_kind == "powerup":
		p.sprite.scale = Vector2(0.55, 0.55)
	p.add_child(p.sprite)
	if p_kind == "powerup" or p_kind == "gem":
		var glow := Sprite2D.new()
		glow.texture = SpriteLib.tex("res://assets/effects/light_01.png")
		glow.scale = Vector2(0.9, 0.9)
		glow.modulate = Color(1, 0.9, 0.5, 0.45) if p_kind == "gem" else Color(0.6, 0.8, 1, 0.5)
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		glow.material = mat
		glow.show_behind_parent = true
		p.add_child(glow)
		p.move_child(glow, 0)
	return p


func _ready() -> void:
	_base_y = position.y
	_t = randf() * TAU
	body_entered.connect(_on_body_entered)


func _process(delta: float) -> void:
	if _taken or flying:
		return
	_t += delta
	position.y = _base_y + sin(_t * 3.0) * 5.0
	if kind == "coin":
		sprite.scale.x = 0.75 * cos(_t * 2.6)
	if magnet_target and is_instance_valid(magnet_target):
		var d := magnet_target.global_position + Vector2(0, -50) - global_position
		if d.length() < 220:
			_base_y += d.normalized().y * 600 * delta
			position.x += d.normalized().x * 600 * delta


func _on_body_entered(body: Node) -> void:
	if _taken or flying or not body.is_in_group("player"):
		return
	_taken = true
	set_deferred("monitoring", false)
	if body.has_method("collect"):
		body.collect(self)
	var t := create_tween().set_parallel(true)
	t.tween_property(self, "position:y", position.y - 60, 0.25).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "scale", Vector2(1.4, 1.4), 0.25)
	t.tween_property(self, "modulate:a", 0.0, 0.25)
	t.chain().tween_callback(queue_free)
