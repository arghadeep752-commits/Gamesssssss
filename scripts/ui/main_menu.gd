extends MenuScreen
## Main menu: logo, Play / Continue / Characters / Shop / Settings, coin + gem indicators.


func _ready() -> void:
	setup_screen("", 1, false)
	AudioManager.play_music("menu", 1.0)
	var vp := get_viewport_rect().size
	# logo
	var logo_box := VBoxContainer.new()
	logo_box.add_theme_constant_override("separation", -18)
	content.add_child(logo_box)
	var ninja := UITheme.make_title("NINJA", 150, Color(1, 0.86, 0.35))
	ninja.add_theme_font_override("font", UITheme.font_bold)
	logo_box.add_child(ninja)
	var ribbon := TextureRect.new()
	ribbon.texture = UITheme.tex("panels/banner_classic_curtain.png")
	ribbon.custom_minimum_size = Vector2(600, 120)
	ribbon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ribbon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	logo_box.add_child(ribbon)
	var sub := UITheme.make_title("SHADOW LEGACY", 46, Color(1, 1, 1))
	sub.set_anchors_preset(Control.PRESET_FULL_RECT)
	sub.position.y = -10
	ribbon.add_child(sub)
	# ninja hero standing on the right of the buttons
	var preview := make_ninja_preview(SaveManager.selected_character(), Vector2(200, 240), 1.6)
	preview.position = Vector2(vp.x - 200, vp.y - 420)
	add_child(preview)
	var spr: AnimatedSprite2D = preview.get_node("Ninja")
	spr.flip_h = true
	var t := create_tween().set_loops()
	t.tween_interval(3.5)
	t.tween_callback(func(): spr.play("attack"))
	t.tween_interval(0.5)
	t.tween_callback(func(): spr.play("idle"))
	var space := Control.new()
	space.custom_minimum_size = Vector2(0, 30)
	content.add_child(space)
	var buttons := VBoxContainer.new()
	buttons.add_theme_constant_override("separation", 18)
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	content.add_child(buttons)
	var play := UITheme.make_button("PLAY", "green", Vector2(470, 124), 50, UITheme.icon("icon_play"))
	play.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/world_select.tscn"))
	_center(buttons, play)
	var cont := UITheme.make_button("CONTINUE", "yellow", Vector2(470, 108), 40)
	var last := int(SaveManager.data.last_level)
	cont.text = "CONTINUE  %d-%d" % [GameData.level(last).world, (last - 1) % 4 + 1]
	cont.pressed.connect(func(): SceneManager.start_level(min(last, int(SaveManager.data.unlocked_level)), true))
	_center(buttons, cont)
	var chars := UITheme.make_button("CHARACTERS", "blue", Vector2(470, 108), 40)
	chars.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/character_select.tscn"))
	_center(buttons, chars)
	var shop := UITheme.make_button("SHOP", "red", Vector2(470, 108), 40, UITheme.icon("icon_money"))
	shop.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/shop.tscn"))
	_center(buttons, shop)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 28)
	buttons.add_child(row)
	var inv := UITheme.make_round_button(UITheme.icon("icon_sword"), "yellow", 112)
	inv.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/inventory.tscn"))
	row.add_child(inv)
	var settings := UITheme.make_round_button(UITheme.icon("icon_cog"), "blue", 112)
	settings.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/settings.tscn"))
	row.add_child(settings)
	var credits := UITheme.make_round_button(UITheme.icon("icon_star"), "green", 112)
	credits.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/credits.tscn"))
	row.add_child(credits)
	var labels := HBoxContainer.new()
	labels.alignment = BoxContainer.ALIGNMENT_CENTER
	labels.add_theme_constant_override("separation", 28)
	buttons.add_child(labels)
	for txt in ["WEAPONS", "SETTINGS", "CREDITS"]:
		var l := UITheme.make_label(txt, 20, Color(1, 1, 1, 0.85), true)
		l.custom_minimum_size = Vector2(112, 0)
		labels.add_child(l)
	var foot := Control.new()
	foot.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(foot)
	var studio := UITheme.make_label("© MXYAN GAMES  •  v1.0", 22, Color(1, 1, 1, 0.7))
	content.add_child(studio)
	UITheme.animate_in(self)


func _center(parent: Control, c: Control) -> void:
	c.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	parent.add_child(c)


func _on_back_key() -> void:
	UITheme.popup(self, "QUIT?", "Leave Ninja: Shadow Legacy?", [["STAY", "green", Callable()], ["QUIT", "red", func(): get_tree().quit()]])
