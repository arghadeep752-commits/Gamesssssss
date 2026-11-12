class_name GameOverlays
extends CanvasLayer
## Level Completed, Game Over, Boss Introduction and Victory screens shown over gameplay.

var _root: Control


func _ready() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UITheme.theme
	add_child(_root)


func _clear() -> void:
	for c in _root.get_children():
		c.queue_free()


func _screen(dim_alpha := 0.7) -> VBoxContainer:
	_clear()
	_root.mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.01, 0.05, dim_alpha)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 20)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_child(v)
	_root.modulate.a = 0.0
	create_tween().tween_property(_root, "modulate:a", 1.0, 0.3)
	return v


# ------------------------------------------------------- level complete
func show_level_complete(level_name: String, stars: int, coins: int, gems: int, time: float, reward: int, has_next: bool, on_next: Callable, on_retry: Callable, on_map: Callable) -> void:
	var v := _screen()
	var banner := TextureRect.new()
	banner.texture = UITheme.tex("panels/banner_hanging.png")
	banner.custom_minimum_size = Vector2(620, 150)
	banner.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	v.add_child(banner)
	var title := UITheme.make_title("LEVEL COMPLETE!", 50)
	title.set_anchors_preset(Control.PRESET_FULL_RECT)
	title.position.y = -18
	banner.add_child(title)
	v.add_child(UITheme.make_label(level_name, 32, Color(1, 0.95, 0.8), true))
	var star_row := HBoxContainer.new()
	star_row.alignment = BoxContainer.ALIGNMENT_CENTER
	star_row.add_theme_constant_override("separation", 18)
	v.add_child(star_row)
	for i in 3:
		var s := TextureRect.new()
		s.texture = UITheme.tex("buttons/yellow/star_outline.png")
		s.custom_minimum_size = Vector2(130, 122)
		s.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		s.pivot_offset = Vector2(65, 61)
		star_row.add_child(s)
		if i < stars:
			var t := create_tween()
			t.tween_interval(0.45 + i * 0.35)
			t.tween_callback(func():
				s.texture = UITheme.tex("buttons/yellow/star.png")
				s.scale = Vector2(1.6, 1.6)
				AudioManager.play_sfx("gem", 0.0))
			t.tween_property(s, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK)
	var panel := UITheme.make_panel("dark")
	v.add_child(panel)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 40)
	grid.add_theme_constant_override("v_separation", 8)
	panel.add_child(grid)
	for row in [["Coins", str(coins)], ["Gems", str(gems)], ["Time", "%d:%02d" % [int(time) / 60, int(time) % 60]], ["Clear bonus", "+%d" % reward]]:
		grid.add_child(UITheme.make_label(row[0], 30, Color(0.9, 0.85, 1), false, HORIZONTAL_ALIGNMENT_LEFT))
		grid.add_child(UITheme.make_label(row[1], 30, Color(1, 0.85, 0.3), true, HORIZONTAL_ALIGNMENT_RIGHT))
	if has_next:
		var nb := UITheme.make_button("NEXT LEVEL", "green", Vector2(480, 110))
		nb.pressed.connect(on_next)
		v.add_child(nb)
	var row2 := HBoxContainer.new()
	row2.alignment = BoxContainer.ALIGNMENT_CENTER
	row2.add_theme_constant_override("separation", 16)
	v.add_child(row2)
	var rb := UITheme.make_button("RETRY", "yellow", Vector2(232, 100), 32)
	rb.pressed.connect(on_retry)
	row2.add_child(rb)
	var mb := UITheme.make_button("MAP", "blue", Vector2(232, 100), 32)
	mb.pressed.connect(on_map)
	row2.add_child(mb)
	AudioManager.play_sfx("level_complete", 0.0)


# ------------------------------------------------------------ game over
func show_game_over(on_retry: Callable, on_map: Callable) -> void:
	var v := _screen(0.8)
	var t := UITheme.make_title("DEFEATED", 84, Color(1, 0.35, 0.3))
	v.add_child(t)
	v.add_child(UITheme.make_label("The shadows claim another warrior...", 28, Color(0.85, 0.8, 0.95)))
	var rb := UITheme.make_button("TRY AGAIN", "green", Vector2(460, 112))
	rb.pressed.connect(on_retry)
	v.add_child(rb)
	var mb := UITheme.make_button("WORLD MAP", "blue", Vector2(460, 112))
	mb.pressed.connect(on_map)
	v.add_child(mb)
	AudioManager.play_sfx("game_over", 0.0)
	AudioManager.play_sfx("game_over_voice", 0.0)


# ---------------------------------------------------------- boss intro
func show_boss_intro(boss_name: String, title: String, duration: float) -> void:
	_clear()
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.modulate.a = 1.0
	var vp := get_viewport().get_visible_rect().size
	var top := ColorRect.new()
	top.color = Color.BLACK
	top.size = Vector2(vp.x, 150)
	top.position = Vector2(0, -150)
	_root.add_child(top)
	var bottom := ColorRect.new()
	bottom.color = Color.BLACK
	bottom.size = Vector2(vp.x, 150)
	bottom.position = Vector2(0, vp.y)
	_root.add_child(bottom)
	var name_l := UITheme.make_title(boss_name, 64, Color(1, 0.4, 0.3))
	name_l.size = Vector2(vp.x, 90)
	name_l.position = Vector2(vp.x, vp.y * 0.38)
	_root.add_child(name_l)
	var sub := UITheme.make_label(title, 30, Color(1, 0.92, 0.8), true)
	sub.size = Vector2(vp.x, 50)
	sub.position = Vector2(-vp.x, vp.y * 0.38 + 90)
	_root.add_child(sub)
	var t := create_tween().set_parallel(true)
	t.tween_property(top, "position:y", 0.0, 0.35)
	t.tween_property(bottom, "position:y", vp.y - 150, 0.35)
	t.tween_property(name_l, "position:x", 0.0, 0.45).set_delay(0.3).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	t.tween_property(sub, "position:x", 0.0, 0.45).set_delay(0.45).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
	var t2 := create_tween()
	t2.tween_interval(duration - 0.5)
	t2.tween_callback(func():
		var fight := UITheme.make_title("FIGHT!", 110, Color(1, 0.85, 0.3))
		fight.size = Vector2(vp.x, 140)
		fight.position = Vector2(0, vp.y * 0.55)
		fight.pivot_offset = Vector2(vp.x / 2.0, 70)
		fight.scale = Vector2(2.2, 2.2)
		_root.add_child(fight)
		AudioManager.play_sfx("boss_fight", 0.0)
		var ft := create_tween()
		ft.tween_property(fight, "scale", Vector2.ONE, 0.2).set_trans(Tween.TRANS_BACK)
		ft.tween_interval(0.5)
		ft.tween_property(fight, "modulate:a", 0.0, 0.3))
	t2.tween_property(top, "position:y", -150.0, 0.3)
	t2.parallel().tween_property(bottom, "position:y", vp.y, 0.3)
	t2.parallel().tween_property(name_l, "modulate:a", 0.0, 0.3)
	t2.parallel().tween_property(sub, "modulate:a", 0.0, 0.3)
	t2.tween_interval(0.6)
	t2.tween_callback(_clear)


func show_banner(text: String, color: Color, time := 2.0) -> void:
	var vp := get_viewport().get_visible_rect().size
	var l := UITheme.make_title(text, 58, color)
	l.size = Vector2(vp.x, 100)
	l.position = Vector2(0, vp.y * 0.33)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.pivot_offset = Vector2(vp.x / 2.0, 50)
	l.scale = Vector2(0.4, 0.4)
	_root.add_child(l)
	var t := create_tween()
	t.tween_property(l, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK)
	t.tween_interval(time)
	t.tween_property(l, "modulate:a", 0.0, 0.4)
	t.tween_callback(l.queue_free)


# -------------------------------------------------------------- victory
func show_victory(on_credits: Callable, on_menu: Callable) -> void:
	var v := _screen(0.85)
	v.add_child(UITheme.make_title("VICTORY!", 96, Color(1, 0.85, 0.3)))
	var story := UITheme.make_label("The Shadow King has fallen.\nLight returns to the six realms,\nand the legacy of the Shadow Clan\nlives on in you, Ninja.", 30, Color(0.95, 0.92, 1))
	story.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	story.custom_minimum_size = Vector2(620, 0)
	v.add_child(story)
	var cb := UITheme.make_button("CREDITS", "yellow", Vector2(460, 110))
	cb.pressed.connect(on_credits)
	v.add_child(cb)
	var mb := UITheme.make_button("MAIN MENU", "blue", Vector2(460, 110))
	mb.pressed.connect(on_menu)
	v.add_child(mb)
	AudioManager.play_music("victory", 1.0)
