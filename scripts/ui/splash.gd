extends Control
## MXYAN GAMES studio splash: black screen -> logo animation + sound -> loading -> main menu.
## Tap to skip.

var _skipped := false
var _done := false


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	theme = UITheme.theme
	var bg := ColorRect.new()
	bg.color = Color.BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var vp := get_viewport_rect().size
	var center := vp / 2.0 + Vector2(0, -40)
	# red sun disc behind the logo
	var sun := Sprite2D.new()
	sun.texture = SpriteLib.tex("res://assets/effects/circle_05.png")
	sun.modulate = Color(0.85, 0.12, 0.12, 0.0)
	sun.position = center + Vector2(0, -20)
	sun.scale = Vector2(0.2, 0.2)
	add_child(sun)
	var glow := Sprite2D.new()
	glow.texture = SpriteLib.tex("res://assets/effects/light_01.png")
	glow.material = Effects.add_material()
	glow.modulate = Color(1, 0.3, 0.2, 0.0)
	glow.position = sun.position
	glow.scale = Vector2(4, 4)
	add_child(glow)
	var logo := UITheme.make_title("MXYAN", 120, Color(1, 0.86, 0.35))
	logo.size = Vector2(vp.x, 150)
	logo.position = Vector2(0, center.y - 110)
	logo.pivot_offset = Vector2(vp.x / 2.0, 75)
	logo.modulate.a = 0.0
	logo.scale = Vector2(1.4, 1.4)
	add_child(logo)
	var games := UITheme.make_label("G  A  M  E  S", 44, Color(1, 1, 1), true)
	games.size = Vector2(vp.x, 60)
	games.position = Vector2(0, center.y + 40)
	games.modulate.a = 0.0
	add_child(games)
	var kunai := Sprite2D.new()
	kunai.texture = SpriteLib.tex("res://assets/weapons/kunai.png")
	kunai.position = Vector2(-120, center.y + 20)
	kunai.scale = Vector2(1.6, 1.6)
	add_child(kunai)
	var slash := Sprite2D.new()
	slash.texture = SpriteLib.tex("res://assets/effects/slash_02.png")
	slash.material = Effects.add_material()
	slash.position = center + Vector2(0, -30)
	slash.scale = Vector2(3.4, 1.6)
	slash.rotation = -0.2
	slash.modulate = Color(1, 1, 1, 0)
	add_child(slash)
	var t := create_tween()
	t.tween_interval(0.35)
	t.tween_callback(func(): AudioManager.play_sfx("swing2", 0.0))
	t.tween_property(kunai, "position:x", vp.x + 140, 0.32).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_IN)
	t.parallel().tween_property(slash, "modulate:a", 1.0, 0.1).set_delay(0.12)
	t.tween_callback(func(): AudioManager.play_sfx("logo", 0.0))
	t.tween_property(slash, "modulate:a", 0.0, 0.35)
	t.parallel().tween_property(logo, "modulate:a", 1.0, 0.35)
	t.parallel().tween_property(logo, "scale", Vector2.ONE, 0.5).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(sun, "modulate:a", 0.9, 0.6)
	t.parallel().tween_property(sun, "scale", Vector2(1.5, 1.5), 0.7).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(glow, "modulate:a", 0.35, 0.8)
	t.tween_property(games, "modulate:a", 1.0, 0.4)
	t.tween_interval(1.3)
	t.tween_callback(_finish)


func _input(event: InputEvent) -> void:
	if (event is InputEventScreenTouch and event.pressed) or (event is InputEventKey and event.pressed):
		if not _skipped:
			_skipped = true
			_finish()


func _finish() -> void:
	if _done:
		return
	_done = true
	# warm up the shared sprite library while the fade runs
	SpriteLib.ninja_frames()
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
