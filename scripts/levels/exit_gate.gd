class_name ExitGate
extends Area2D
## Level exit (door with an EXIT sign). Can start locked (boss levels).

signal reached

var locked := false
var _door: Sprite2D
var _door_top: Sprite2D
var _sign: Sprite2D
var _glow: Sprite2D
var _done := false


static func create(p_locked: bool) -> ExitGate:
	var g := ExitGate.new()
	g.locked = p_locked
	g.collision_layer = 0
	g.collision_mask = 2
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(60, 120)
	cs.shape = r
	cs.position = Vector2(0, -40)
	g.add_child(cs)
	g._glow = Sprite2D.new()
	g._glow.texture = SpriteLib.tex("res://assets/effects/light_03.png")
	g._glow.scale = Vector2(2.4, 2.8)
	g._glow.position = Vector2(0, -60)
	g._glow.modulate = Color(1, 0.9, 0.5, 0.5)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	g._glow.material = mat
	g.add_child(g._glow)
	g._door = Sprite2D.new()
	g._door_top = Sprite2D.new()
	g._door.position = Vector2(0, 0)
	g._door_top.position = Vector2(0, -64)
	g.add_child(g._door_top)
	g.add_child(g._door)
	g._sign = Sprite2D.new()
	g._sign.texture = SpriteLib.tex("res://assets/environments/props/sign_exit.png")
	g._sign.position = Vector2(-84, 0)
	g.add_child(g._sign)
	g._refresh()
	return g


func _refresh() -> void:
	var state := "closed" if locked else "open"
	_door.texture = SpriteLib.tex("res://assets/environments/props/door_%s.png" % state)
	_door_top.texture = SpriteLib.tex("res://assets/environments/props/door_%s_top.png" % state)
	_glow.visible = not locked


func _ready() -> void:
	body_entered.connect(func(b):
		if b.is_in_group("player") and not locked and not _done:
			_done = true
			reached.emit())


func unlock() -> void:
	locked = false
	_refresh()
	modulate = Color(2, 2, 2)
	create_tween().tween_property(self, "modulate", Color.WHITE, 0.6)
	for b in get_overlapping_bodies():
		if b.is_in_group("player") and not _done:
			_done = true
			reached.emit()
