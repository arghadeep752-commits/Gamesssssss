class_name Checkpoint
extends Area2D
## Flag that stores the respawn point (and saves it so the level can be resumed).

signal activated(cp: Checkpoint)

var index := 0
var active := false
var _sprite: AnimatedSprite2D
var _glow: Sprite2D


static func create(p_index: int) -> Checkpoint:
	var c := Checkpoint.new()
	c.index = p_index
	c.collision_layer = 0
	c.collision_mask = 2
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(70, 130)
	cs.shape = r
	cs.position = Vector2(0, -40)
	c.add_child(cs)
	var sf := SpriteFrames.new()
	sf.add_animation("off")
	sf.add_frame("off", SpriteLib.tex("res://assets/environments/props/flag_off.png"))
	sf.add_animation("on")
	sf.set_animation_speed("on", 5)
	sf.add_frame("on", SpriteLib.tex("res://assets/environments/props/flag_green_a.png"))
	sf.add_frame("on", SpriteLib.tex("res://assets/environments/props/flag_green_b.png"))
	c._sprite = AnimatedSprite2D.new()
	c._sprite.sprite_frames = sf
	c._sprite.animation = "off"
	c._sprite.position = Vector2(0, 0)
	c._sprite.scale = Vector2(1.25, 1.25)
	c.add_child(c._sprite)
	c._glow = Sprite2D.new()
	c._glow.texture = SpriteLib.tex("res://assets/effects/light_01.png")
	c._glow.modulate = Color(0.5, 1.0, 0.6, 0.0)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	c._glow.material = mat
	c._glow.scale = Vector2(2, 2)
	c.add_child(c._glow)
	return c


func _ready() -> void:
	body_entered.connect(func(b):
		if not active and b.is_in_group("player"):
			activate(true))


func activate(announce: bool) -> void:
	active = true
	_sprite.play("on")
	if announce:
		AudioManager.play_sfx("checkpoint", 0.0)
		Haptics.medium()
		var t := create_tween()
		t.tween_property(_glow, "modulate:a", 0.8, 0.15)
		t.tween_property(_glow, "modulate:a", 0.25, 0.6)
		activated.emit(self)
	else:
		_glow.modulate.a = 0.25
