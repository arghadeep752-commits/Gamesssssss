extends MenuScreen
## World selection: six realms with stars and lock state.


func _ready() -> void:
	setup_screen("SELECT WORLD", 6)
	AudioManager.play_music("menu", 1.0)
	var list := scroll_area()
	for w in GameData.WORLDS:
		list.add_child(_card(w))
	UITheme.animate_in(self)


func _card(w: Dictionary) -> Control:
	var unlocked := SaveManager.is_world_unlocked(w.id)
	var b := UITheme.make_square_button("blue" if unlocked else "grey", Vector2(660, 190))
	b.disabled = not unlocked
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var clip := Control.new()
	clip.clip_contents = true
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.position = Vector2(14, 12)
	clip.size = Vector2(632, 150)
	b.add_child(clip)
	var sky := ColorRect.new()
	sky.color = w.sky_bottom
	sky.size = clip.size
	sky.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(sky)
	var art := TextureRect.new()
	art.texture = SpriteLib.tex("res://assets/backgrounds/background_color_%s.png" % w.bg)
	art.stretch_mode = TextureRect.STRETCH_TILE
	art.size = Vector2(632, 256)
	art.position = Vector2(0, -70)
	art.modulate = w.layer_tint if unlocked else Color(0.35, 0.35, 0.4)
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(art)
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.35)
	shade.size = clip.size
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(shade)
	var name_l := UITheme.make_label("WORLD %d" % w.id, 26, Color(1, 0.86, 0.4), true, HORIZONTAL_ALIGNMENT_LEFT)
	name_l.position = Vector2(24, 18)
	name_l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(name_l)
	var title := UITheme.make_label(w.name.to_upper(), 36, Color.WHITE, true, HORIZONTAL_ALIGNMENT_LEFT)
	title.position = Vector2(24, 50)
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(title)
	var sub := UITheme.make_label(w.subtitle, 24, Color(0.9, 0.9, 1), false, HORIZONTAL_ALIGNMENT_LEFT)
	sub.position = Vector2(24, 102)
	sub.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(sub)
	var right := HBoxContainer.new()
	right.position = Vector2(500, 14)
	right.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(right)
	if unlocked:
		var star := TextureRect.new()
		star.texture = UITheme.tex("buttons/yellow/star.png")
		star.custom_minimum_size = Vector2(44, 42)
		star.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		star.mouse_filter = Control.MOUSE_FILTER_IGNORE
		right.add_child(star)
		var sl := UITheme.make_label("%d/12" % SaveManager.world_stars(w.id), 30, Color.WHITE, true)
		sl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		right.add_child(sl)
	else:
		var lock := TextureRect.new()
		lock.texture = UITheme.icon("icon_lock")
		lock.custom_minimum_size = Vector2(60, 60)
		lock.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		lock.mouse_filter = Control.MOUSE_FILTER_IGNORE
		right.position = Vector2(548, 16)
		right.add_child(lock)
	var boss_name: String = GameData.BOSSES[w.boss].name
	var bl := UITheme.make_label("Boss: " + boss_name.capitalize(), 20, Color(1, 0.6, 0.55), true, HORIZONTAL_ALIGNMENT_RIGHT)
	bl.position = Vector2(330, 112)
	bl.size = Vector2(280, 30)
	bl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(bl)
	b.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/level_select.tscn", {"world": w.id}))
	return b


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
