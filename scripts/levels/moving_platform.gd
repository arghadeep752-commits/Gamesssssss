class_name MovingPlatform
extends AnimatableBody2D
## One-way platform made from terrain cloud tiles that travels back and forth.

var travel := Vector2(256, 0)
var period := 4.0
var _origin := Vector2.ZERO
var _t := 0.0


static func create(atlas: Texture2D, terrain_row: int, p_travel: Vector2, p_period: float) -> MovingPlatform:
	var m := MovingPlatform.new()
	m.travel = p_travel
	m.period = p_period
	m.collision_layer = 1
	m.collision_mask = 0
	m.sync_to_physics = true
	for i in 3:
		var s := Sprite2D.new()
		var at := AtlasTexture.new()
		at.atlas = atlas
		at.region = Rect2((13 + i) * 64, terrain_row * 64, 64, 64)
		s.texture = at
		s.position = Vector2((i - 1) * 64, 0)
		m.add_child(s)
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(186, 22)
	cs.shape = r
	cs.position = Vector2(0, -15)
	cs.one_way_collision = true
	m.add_child(cs)
	return m


func _ready() -> void:
	_origin = position
	_t = randf() * period


func _physics_process(delta: float) -> void:
	_t += delta
	var k := sin(_t / period * TAU)
	position = _origin + travel * k
