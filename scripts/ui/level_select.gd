extends MenuScreen
## Level selection for one world (4 levels, boss on the last one).

var world_id := 1


func _ready() -> void:
	world_id = int(SceneManager.params.get("world", GameData.level(SaveManager.data.last_level).world))
	var w := GameData.world(world_id)
	setup_screen(w.name.to_upper(), world_id, true, "res://scenes/menus/world_select.tscn")
	AudioManager.play_music(w.music, 1.0)
	var sub := UITheme.make_label(w.subtitle, 28, Color(0.95, 0.92, 1))
	content.add_child(sub)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 26)
	grid.add_theme_constant_override("v_separation", 26)
	grid.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	content.add_child(grid)
	for i in 4:
		grid.add_child(_level_button((world_id - 1) * 4 + i + 1))
	var info := UITheme.make_label("Collect 70% of coins and finish without losing a life for 3 stars.", 24, Color(1, 1, 1, 0.8))
	info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	info.custom_minimum_size = Vector2(620, 0)
	content.add_child(info)
	UITheme.animate_in(self)


func _level_button(index: int) -> Control:
	var lv := GameData.level(index)
	var unlocked := SaveManager.is_level_unlocked(index)
	var boss := GameData.is_boss_level(index)
	var b := UITheme.make_square_button(("red" if boss else "blue") if unlocked else "grey", Vector2(300, 330))
	b.disabled = not unlocked
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 14
	v.offset_right = -14
	v.offset_top = 14
	v.offset_bottom = -26
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 6)
	b.add_child(v)
	var num := UITheme.make_title("%d-%d" % [world_id, (index - 1) % 4 + 1], 72, Color.WHITE)
	num.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(num)
	var name_l := UITheme.make_label(lv.display_name, 26, Color(1, 0.95, 0.8), true)
	name_l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_l.custom_minimum_size = Vector2(260, 64)
	name_l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(name_l)
	if not unlocked:
		var lock := TextureRect.new()
		lock.texture = UITheme.icon("icon_lock")
		lock.custom_minimum_size = Vector2(70, 70)
		lock.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		lock.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		lock.mouse_filter = Control.MOUSE_FILTER_IGNORE
		v.add_child(lock)
	else:
		var stars := HBoxContainer.new()
		stars.alignment = BoxContainer.ALIGNMENT_CENTER
		stars.mouse_filter = Control.MOUSE_FILTER_IGNORE
		v.add_child(stars)
		var got := SaveManager.level_stars(index)
		for i in 3:
			var s := TextureRect.new()
			s.texture = UITheme.tex("buttons/yellow/star.png" if i < got else "buttons/yellow/star_outline.png")
			s.custom_minimum_size = Vector2(56, 52)
			s.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			s.mouse_filter = Control.MOUSE_FILTER_IGNORE
			stars.add_child(s)
		var tag := ""
		if boss:
			tag = "BOSS"
		if not SaveManager.get_checkpoint(index).is_empty():
			tag = "CHECKPOINT SAVED" if tag == "" else tag + " • CHECKPOINT"
		if tag != "":
			var tl := UITheme.make_label(tag, 18, Color(1, 0.7, 0.4) if boss else Color(0.6, 1, 0.7), true)
			tl.mouse_filter = Control.MOUSE_FILTER_IGNORE
			v.add_child(tl)
	b.pressed.connect(func(): SceneManager.start_level(index, true))
	return b


func _back_params() -> Dictionary:
	return {}


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/world_select.tscn")
