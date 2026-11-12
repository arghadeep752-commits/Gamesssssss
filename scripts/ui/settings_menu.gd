extends MenuScreen
## Settings: audio, vibration, graphics, controls (sensitivity / size / opacity / layout editor),
## language, privacy, credits, reset progress.

const PRIVACY := "Ninja: Shadow Legacy works fully offline. It does not collect, store or send any personal data. Your progress is saved only on this device. There are no ads and no real-money purchases."

var _editor: CanvasLayer


func _ready() -> void:
	setup_screen("SETTINGS", 3)
	var list := scroll_area()
	var audio := _section(list, "AUDIO")
	audio.add_child(_slider("Music", "music"))
	audio.add_child(_slider("Sound FX", "sfx"))
	var game := _section(list, "GAMEPLAY")
	var vib := CheckBox.new()
	vib.text = "  Vibration feedback"
	vib.button_pressed = bool(SaveManager.setting("vibration"))
	vib.toggled.connect(func(on):
		SaveManager.set_setting("vibration", on)
		if on:
			Haptics.medium())
	game.add_child(vib)
	var fps := CheckBox.new()
	fps.text = "  Show FPS counter"
	fps.button_pressed = bool(SaveManager.setting("show_fps"))
	fps.toggled.connect(func(on): SaveManager.set_setting("show_fps", on))
	game.add_child(fps)
	game.add_child(UITheme.make_label("Graphics quality", 26, Color.WHITE, true, HORIZONTAL_ALIGNMENT_LEFT))
	var q_row := HBoxContainer.new()
	q_row.add_theme_constant_override("separation", 10)
	game.add_child(q_row)
	var q_buttons := []
	for i in 3:
		var b := UITheme.make_button(["LOW", "MEDIUM", "HIGH"][i], "grey", Vector2(190, 80), 26)
		q_row.add_child(b)
		q_buttons.append(b)
	var refresh_q := func():
		for i in 3:
			var st := UITheme.button_styles("green" if int(SaveManager.setting("quality")) == i else "grey")
			for k in st:
				q_buttons[i].add_theme_stylebox_override(k, st[k])
	for i in 3:
		q_buttons[i].pressed.connect(func():
			SaveManager.set_setting("quality", i)
			refresh_q.call())
	refresh_q.call()
	var ctl := _section(list, "CONTROLS")
	ctl.add_child(_slider("Joystick sensitivity", "sensitivity"))
	ctl.add_child(_slider("Button size", "controls_scale", 0.7, 1.3))
	ctl.add_child(_slider("Button opacity", "controls_opacity", 0.3, 1.0))
	var edit := UITheme.make_button("EDIT BUTTON LAYOUT", "blue", Vector2(600, 96), 30)
	edit.pressed.connect(_open_layout_editor)
	ctl.add_child(edit)
	var other := _section(list, "OTHER")
	var lang_row := HBoxContainer.new()
	lang_row.add_child(UITheme.make_label("Language", 26, Color.WHITE, true, HORIZONTAL_ALIGNMENT_LEFT))
	var lang := OptionButton.new()
	lang.add_item("English", 0)
	lang.custom_minimum_size = Vector2(260, 60)
	lang.add_theme_font_size_override("font_size", 26)
	lang.item_selected.connect(func(_i):
		SaveManager.set_setting("language", "en")
		TranslationServer.set_locale("en"))
	lang_row.add_child(lang)
	other.add_child(lang_row)
	var priv := UITheme.make_button("PRIVACY", "grey", Vector2(600, 90), 28)
	priv.pressed.connect(func(): UITheme.popup(self, "PRIVACY", PRIVACY, [["OK", "blue", Callable()]]))
	other.add_child(priv)
	var cred := UITheme.make_button("CREDITS", "yellow", Vector2(600, 90), 28)
	cred.pressed.connect(func(): SceneManager.goto_menu("res://scenes/menus/credits.tscn"))
	other.add_child(cred)
	var reset := UITheme.make_button("RESET PROGRESS", "red", Vector2(600, 90), 28)
	reset.pressed.connect(func(): UITheme.popup(self, "RESET?", "This deletes ALL progress, coins, gems, ninjas and weapons. This cannot be undone.", [["CANCEL", "green", Callable()], ["RESET", "red", _do_reset]]))
	other.add_child(reset)


func _do_reset() -> void:
	SaveManager.reset_progress()
	UITheme.toast(self, "PROGRESS RESET", Color(1, 0.5, 0.4))


func _section(parent: Control, title: String) -> VBoxContainer:
	var panel := UITheme.make_panel("brown")
	panel.custom_minimum_size = Vector2(660, 0)
	panel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	parent.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	panel.add_child(v)
	v.add_child(UITheme.make_label(title, 34, Color(1, 0.86, 0.4), true, HORIZONTAL_ALIGNMENT_LEFT))
	return v


func _slider(label: String, key: String, min_v := 0.0, max_v := 1.0) -> Control:
	var v := VBoxContainer.new()
	var row := HBoxContainer.new()
	v.add_child(row)
	var l := UITheme.make_label(label, 26, Color.WHITE, false, HORIZONTAL_ALIGNMENT_LEFT)
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(l)
	var val := UITheme.make_label("", 24, Color(1, 0.86, 0.4), true, HORIZONTAL_ALIGNMENT_RIGHT)
	row.add_child(val)
	var s := UITheme.make_slider(float(SaveManager.setting(key)))
	s.min_value = min_v
	s.max_value = max_v
	s.step = 0.05
	s.value = float(SaveManager.setting(key))
	s.custom_minimum_size = Vector2(600, 48)
	val.text = "%d%%" % int(s.value * 100)
	s.value_changed.connect(func(x):
		SaveManager.set_setting(key, x)
		val.text = "%d%%" % int(x * 100))
	v.add_child(s)
	return v


func _open_layout_editor() -> void:
	_editor = CanvasLayer.new()
	_editor.layer = 40
	add_child(_editor)
	var dim := ColorRect.new()
	dim.color = Color(0.05, 0.04, 0.1, 0.85)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_editor.add_child(dim)
	var tip := UITheme.make_label("Drag the controls to where your thumbs feel comfortable.", 30, Color.WHITE, true)
	tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	tip.set_anchors_preset(Control.PRESET_CENTER_TOP)
	tip.position = Vector2(-320, 160)
	tip.size = Vector2(640, 120)
	_editor.add_child(tip)
	var tc := TouchControls.new()
	tc.edit_mode = true
	_editor.add_child(tc)
	var box := HBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_CENTER_TOP)
	box.position = Vector2(-300, 320)
	box.add_theme_constant_override("separation", 20)
	_editor.add_child(box)
	var reset := UITheme.make_button("RESET", "red", Vector2(280, 96), 30)
	reset.pressed.connect(func(): tc.reset_layout())
	box.add_child(reset)
	var done := UITheme.make_button("DONE", "green", Vector2(280, 96), 30)
	done.pressed.connect(func():
		_editor.queue_free()
		_editor = null)
	box.add_child(done)


func _on_back_key() -> void:
	if _editor:
		_editor.queue_free()
		_editor = null
		return
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
