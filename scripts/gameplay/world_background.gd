class_name WorldBackground
extends Node2D
## Parallax background built from Kenney background art + world colour grading,
## plus ambient particles (sakura petals, leaves, snow, embers, magic).

const BG := "res://assets/backgrounds/"
const EL := "res://assets/backgrounds/elements/"

var world: Dictionary
var level_size := Vector2(10000, 1408)
var _particles: CPUParticles2D


func build(p_world: Dictionary, p_size: Vector2, camera: Camera2D, seed_value: int) -> void:
	world = p_world
	level_size = p_size
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	# --- sky gradient fixed to the screen
	var sky_layer := CanvasLayer.new()
	sky_layer.layer = -20
	add_child(sky_layer)
	var sky := ColorRect.new()
	sky.set_anchors_preset(Control.PRESET_FULL_RECT)
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/sky_gradient.gdshader")
	m.set_shader_parameter("top_color", world.sky_top)
	m.set_shader_parameter("bottom_color", world.sky_bottom)
	sky.material = m
	sky.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sky_layer.add_child(sky)
	var ground_y := 17 * 64.0
	# --- far celestial / clouds
	var far := _parallax(Vector2(0.04, 0.05), 0.0)
	for name in world.far:
		var s := Sprite2D.new()
		s.texture = SpriteLib.tex(EL + name + ".png")
		if name in ["sun", "moon", "moonFull"]:
			s.position = Vector2(560, 180)
			s.scale = Vector2(1.6, 1.6)
			s.modulate = Color(1, 1, 1, 0.95)
			if name != "sun":
				Effects.light(far, s.position, Color(0.8, 0.8, 1.0, 0.35), 5.0)
		else:
			s.position = Vector2(rng.randf_range(0, 2400), rng.randf_range(80, 420))
			s.scale = Vector2.ONE * rng.randf_range(0.8, 1.4)
			s.modulate = Color(1, 1, 1, 0.75) * Color(world.layer_tint, 1.0).lightened(0.5)
		far.add_child(s)
	far.repeat_size = Vector2(2400, 0)
	# --- Kenney background bands (fade = distant hills, color = closer hills/trees)
	var bg: String = world.bg
	_band("background_fade_%s.png" % bg, Vector2(0.15, 0.12), ground_y - 360, 3.0, Color(world.layer_tint).lightened(0.25))
	_band("background_color_%s.png" % bg, Vector2(0.32, 0.25), ground_y - 200, 3.2, world.layer_tint)
	# --- silhouettes (trees, houses, towers, castles)
	var mid := _parallax(Vector2(0.55, 0.55), 0.0)
	var x := 0.0
	var span := 3600.0
	while x < span:
		var name: String = world.elements[rng.randi_range(0, world.elements.size() - 1)]
		var s := Sprite2D.new()
		s.texture = SpriteLib.tex(EL + name + ".png")
		s.centered = false
		var sc := rng.randf_range(1.5, 2.3)
		s.scale = Vector2(sc, sc)
		s.position = Vector2(x, ground_y + 120 - s.texture.get_height() * sc)
		s.modulate = Color(world.layer_tint).darkened(0.18)
		mid.add_child(s)
		x += s.texture.get_width() * sc * rng.randf_range(0.7, 1.5)
	mid.repeat_size = Vector2(span, 0)
	# --- colour grading of the whole playfield
	var cm := CanvasModulate.new()
	cm.color = world.modulate
	add_child(cm)
	_add_particles(camera)


func _parallax(scroll: Vector2, y: float) -> Parallax2D:
	var p := Parallax2D.new()
	p.scroll_scale = scroll
	p.position = Vector2(0, y)
	p.ignore_camera_scroll = false
	p.z_index = -50
	add_child(p)
	return p


func _band(file: String, scroll: Vector2, top_y: float, sc: float, tint: Color) -> void:
	var tex := SpriteLib.tex(BG + file)
	if tex == null:
		return
	var p := _parallax(scroll, 0.0)
	var w := tex.get_width() * sc
	for i in 6:
		var s := Sprite2D.new()
		s.texture = tex
		s.centered = false
		s.scale = Vector2(sc, sc)
		s.position = Vector2(i * w, top_y)
		s.modulate = tint
		p.add_child(s)
	p.repeat_size = Vector2(w * 6, 0)
	# fill below the band so no sky shows under the hills
	var fill := ColorRect.new()
	fill.color = tint.darkened(0.25) * Color(world.sky_bottom).darkened(0.1)
	fill.position = Vector2(0, top_y + tex.get_height() * sc - 4)
	fill.size = Vector2(w * 6, 1200)
	fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(fill)


func _add_particles(camera: Camera2D) -> void:
	var q := int(SaveManager.setting("quality"))
	if q == 0:
		return
	var p := CPUParticles2D.new()
	p.amount = 18 if q == 1 else 34
	p.lifetime = 7.0
	p.preprocess = 4.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(520, 20)
	p.position = Vector2(0, -760)
	p.local_coords = false
	p.direction = Vector2(-0.4, 1)
	p.spread = 20
	p.gravity = Vector2(0, 40)
	p.initial_velocity_min = 40
	p.initial_velocity_max = 110
	p.angular_velocity_min = -90
	p.angular_velocity_max = 90
	p.angle_min = 0
	p.angle_max = 360
	p.z_index = 20
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 0.0))
	ramp.add_point(0.15, Color(1, 1, 1, 1))
	ramp.set_color(ramp.get_point_count() - 1, Color(1, 1, 1, 0))
	p.color_ramp = ramp
	match world.particles:
		"leaf_pink":
			p.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			p.texture = _frame("res://assets/effects/pixel/leaf_pink.png", 12)
			p.scale_amount_min = 2.5
			p.scale_amount_max = 3.5
		"leaf":
			p.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			p.texture = _frame("res://assets/effects/pixel/leaf.png", 12)
			p.scale_amount_min = 2.5
			p.scale_amount_max = 3.5
			p.color = Color(1.0, 0.7, 0.4)
		"snow":
			p.texture = SpriteLib.tex("res://assets/effects/circle_05.png")
			p.scale_amount_min = 0.05
			p.scale_amount_max = 0.1
			p.direction = Vector2(-0.6, 1)
			p.initial_velocity_max = 160
			p.amount = int(p.amount * 1.6)
		"ember":
			p.texture = SpriteLib.tex("res://assets/effects/spark_01.png")
			p.material = Effects.add_material()
			p.color = Color(1, 0.55, 0.2)
			p.scale_amount_min = 0.06
			p.scale_amount_max = 0.14
			p.position = Vector2(0, 700)
			p.direction = Vector2(0.2, -1)
			p.gravity = Vector2(0, -60)
		"spark":
			p.texture = SpriteLib.tex("res://assets/effects/light_01.png")
			p.material = Effects.add_material()
			p.color = Color(0.7, 0.6, 1.0, 0.6)
			p.scale_amount_min = 0.03
			p.scale_amount_max = 0.07
			p.gravity = Vector2(0, -8)
			p.initial_velocity_max = 30
			p.emission_rect_extents = Vector2(520, 700)
			p.position = Vector2(0, 0)
		"magic":
			p.texture = SpriteLib.tex("res://assets/effects/magic_01.png")
			p.material = Effects.add_material()
			p.color = Color(0.7, 0.35, 1.0, 0.7)
			p.scale_amount_min = 0.06
			p.scale_amount_max = 0.14
			p.direction = Vector2(0, -1)
			p.gravity = Vector2(0, -30)
			p.position = Vector2(0, 600)
	camera.add_child(p)
	_particles = p


func _frame(path: String, frame_w: int) -> Texture2D:
	var t := SpriteLib.tex(path)
	if t == null:
		return null
	var at := AtlasTexture.new()
	at.atlas = t
	at.region = Rect2(0, 0, min(frame_w, t.get_width()), t.get_height())
	return at
