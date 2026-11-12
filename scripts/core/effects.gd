class_name Effects
extends RefCounted
## Visual effect helpers (Kenney particle pack + Ninja Adventure FX sprites).

const FX := "res://assets/effects/"
static var _add_mat: CanvasItemMaterial


static func add_material() -> CanvasItemMaterial:
	if _add_mat == null:
		_add_mat = CanvasItemMaterial.new()
		_add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return _add_mat


static func _quality() -> int:
	return int(SaveManager.setting("quality"))


## Quick additive sprite flash that scales and fades.
static func flash(parent: Node, pos: Vector2, tex_name: String, color: Color, from_scale: float, to_scale: float, time := 0.25, rot := 0.0, additive := true) -> Sprite2D:
	if parent == null or not is_instance_valid(parent):
		return null
	var s := Sprite2D.new()
	s.texture = SpriteLib.tex(FX + tex_name + ".png")
	s.global_position = pos
	s.modulate = color
	s.rotation = rot
	s.scale = Vector2(from_scale, from_scale)
	s.z_index = 15
	if additive:
		s.material = add_material()
	parent.add_child(s)
	s.global_position = pos
	var t := s.create_tween().set_parallel(true)
	t.tween_property(s, "scale", Vector2(to_scale, to_scale), time).set_ease(Tween.EASE_OUT)
	t.tween_property(s, "modulate:a", 0.0, time).set_ease(Tween.EASE_IN)
	t.chain().tween_callback(s.queue_free)
	return s


static func slash(parent: Node, pos: Vector2, facing: float, color := Color(1, 1, 1, 0.9), size := 1.0) -> void:
	var s := flash(parent, pos, "slash_0%d" % (randi() % 3 + 1), color, 0.9 * size, 1.4 * size, 0.18)
	if s:
		s.flip_h = facing < 0
		s.rotation = randf_range(-0.3, 0.3)


static func hit_spark(parent: Node, pos: Vector2, color := Color(1, 0.9, 0.6), big := false) -> void:
	flash(parent, pos, "star_06", color, 0.25, 0.9 if big else 0.6, 0.16, randf() * TAU)
	flash(parent, pos, "spark_04", Color(color, 0.8), 0.3, 0.8, 0.2, randf() * TAU)
	if _quality() >= 1:
		burst(parent, pos, "spark_01", color, 8 if big else 5, 260.0, 0.35, 0.12)


static func burst(parent: Node, pos: Vector2, tex_name: String, color: Color, amount: int, speed: float, life := 0.5, size := 0.15, gravity := 400.0) -> void:
	if parent == null or not is_instance_valid(parent):
		return
	var p := CPUParticles2D.new()
	p.texture = SpriteLib.tex(FX + tex_name + ".png")
	p.one_shot = true
	p.explosiveness = 0.95
	p.amount = max(1, amount)
	p.lifetime = life
	p.spread = 180.0
	p.initial_velocity_min = speed * 0.4
	p.initial_velocity_max = speed
	p.gravity = Vector2(0, gravity)
	p.scale_amount_min = size * 0.6
	p.scale_amount_max = size
	p.color = color
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	p.color_ramp = ramp
	p.material = add_material()
	p.z_index = 16
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	p.finished.connect(p.queue_free)


static func dust(parent: Node, pos: Vector2, amount := 6) -> void:
	if _quality() == 0:
		return
	var p := CPUParticles2D.new()
	p.texture = SpriteLib.tex(FX + "smoke_04.png")
	p.one_shot = true
	p.explosiveness = 0.9
	p.amount = amount
	p.lifetime = 0.45
	p.direction = Vector2(0, -1)
	p.spread = 70.0
	p.initial_velocity_min = 40
	p.initial_velocity_max = 140
	p.gravity = Vector2(0, -40)
	p.scale_amount_min = 0.12
	p.scale_amount_max = 0.24
	p.color = Color(1, 0.97, 0.9, 0.55)
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1, 1, 1, 1))
	ramp.set_color(1, Color(1, 1, 1, 0))
	p.color_ramp = ramp
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	p.finished.connect(p.queue_free)


static func debris(parent: Node, pos: Vector2, tex: Texture2D, count := 6) -> void:
	for i in count:
		var s := Sprite2D.new()
		s.texture = tex
		s.region_enabled = true
		var w := 20.0
		s.region_rect = Rect2(randf_range(0, 40), randf_range(0, 40), w, w)
		parent.add_child(s)
		s.global_position = pos + Vector2(randf_range(-20, 20), randf_range(-20, 20))
		var v := Vector2(randf_range(-260, 260), randf_range(-520, -220))
		var end := s.position + v * 0.6 + Vector2(0, 260)
		var t := s.create_tween().set_parallel(true)
		t.tween_property(s, "position", end, 0.6).set_ease(Tween.EASE_IN)
		t.tween_property(s, "rotation", randf_range(-6, 6), 0.6)
		t.tween_property(s, "modulate:a", 0.0, 0.6).set_delay(0.25)
		t.chain().tween_callback(s.queue_free)


static func explosion(parent: Node, pos: Vector2, size := 1.0, color := Color(1, 0.6, 0.25)) -> void:
	flash(parent, pos, "light_03", Color(color, 0.9), 0.4 * size, 2.2 * size, 0.45)
	flash(parent, pos, "flare_01", Color(1, 1, 0.9, 0.9), 0.3 * size, 1.4 * size, 0.3)
	burst(parent, pos, "fire_01", color, 14, 520.0 * size, 0.6, 0.35 * size, 200.0)
	burst(parent, pos, "smoke_07", Color(0.4, 0.35, 0.4, 0.7), 8, 200.0 * size, 0.9, 0.5 * size, -60.0)


static func damage_number(parent: Node, pos: Vector2, amount: float, crit: bool, color := Color.WHITE) -> void:
	var l := Label.new()
	l.text = str(int(round(amount))) + ("!" if crit else "")
	l.add_theme_font_override("font", UITheme.font_bold)
	l.add_theme_font_size_override("font_size", 40 if crit else 30)
	l.add_theme_color_override("font_color", Color(1, 0.85, 0.2) if crit else color)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.0, 0.05))
	l.add_theme_constant_override("outline_size", 8)
	l.z_index = 30
	parent.add_child(l)
	l.global_position = pos + Vector2(-30 + randf_range(-12, 12), -40)
	l.scale = Vector2(0.5, 0.5)
	var t := l.create_tween()
	t.tween_property(l, "scale", Vector2(1.15, 1.15) if crit else Vector2.ONE, 0.1)
	t.parallel().tween_property(l, "position:y", l.position.y - 70, 0.6).set_ease(Tween.EASE_OUT)
	t.tween_property(l, "modulate:a", 0.0, 0.25)
	t.tween_callback(l.queue_free)


## Plays a horizontal pixel-art FX strip (Ninja Adventure) once.
static func strip_fx(parent: Node, pos: Vector2, file: String, frame_w: int, scale := 3.0, fps := 16.0, color := Color.WHITE, flip := false) -> AnimatedSprite2D:
	var a := AnimatedSprite2D.new()
	a.sprite_frames = SpriteLib.strip_frames(FX + "pixel/" + file, frame_w, fps, false)
	a.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	a.scale = Vector2(scale, scale)
	a.modulate = color
	a.flip_h = flip
	a.z_index = 15
	parent.add_child(a)
	a.global_position = pos
	a.play("default")
	a.animation_finished.connect(a.queue_free)
	return a


static func light(parent: Node, pos: Vector2, color: Color, size := 2.0) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = SpriteLib.tex(FX + "light_01.png")
	s.material = add_material()
	s.modulate = color
	s.scale = Vector2(size, size)
	parent.add_child(s)
	s.position = pos
	return s
