extends Control
## Main menu: black background, game name, PLAY, SETTINGS (sensitivity only).

var settings_panel: Panel
var credits_panel: Panel
var sens_label: Label
var sens_slider: HSlider
var loading_label: Label
var buttons: VBoxContainer
var music: AudioStreamPlayer


func _ready() -> void:
	theme = Assets.get_theme()
	set_anchors_preset(Control.PRESET_FULL_RECT)

	var bg := ColorRect.new()
	bg.color = Color.BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var title := Label.new()
	title.text = "SCARY AUNTY"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.anchor_left = 0.0
	title.anchor_right = 1.0
	title.offset_top = 70.0
	title.offset_bottom = 230.0
	title.add_theme_font_size_override("font_size", 120)
	title.add_theme_color_override("font_color", Color(0.95, 0.95, 0.92))
	title.add_theme_color_override("font_outline_color", Color(0.55, 0.0, 0.0))
	title.add_theme_constant_override("outline_size", 14)
	add_child(title)

	var sub := Label.new()
	sub.text = "Escape from the neighbour's house!"
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.anchor_right = 1.0
	sub.offset_top = 225.0
	sub.offset_bottom = 275.0
	sub.add_theme_font_size_override("font_size", 32)
	sub.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	add_child(sub)

	buttons = VBoxContainer.new()
	buttons.set_anchors_preset(Control.PRESET_CENTER)
	buttons.offset_left = -190.0
	buttons.offset_right = 190.0
	buttons.offset_top = -20.0
	buttons.offset_bottom = 170.0
	buttons.add_theme_constant_override("separation", 22)
	add_child(buttons)
	_button(buttons, "PLAY", _on_play)
	_button(buttons, "SETTINGS", _on_settings)

	var footer := Label.new()
	footer.text = "MXYAN GAMES"
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.anchor_top = 1.0
	footer.anchor_bottom = 1.0
	footer.anchor_right = 1.0
	footer.offset_top = -60.0
	footer.offset_bottom = -20.0
	footer.add_theme_font_size_override("font_size", 24)
	footer.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	add_child(footer)

	# Small credits link (needed for the CC-BY models and music).
	var credits_btn := Button.new()
	credits_btn.text = "Credits"
	credits_btn.flat = true
	credits_btn.anchor_left = 1.0
	credits_btn.anchor_right = 1.0
	credits_btn.anchor_top = 1.0
	credits_btn.anchor_bottom = 1.0
	credits_btn.offset_left = -170.0
	credits_btn.offset_right = -20.0
	credits_btn.offset_top = -66.0
	credits_btn.offset_bottom = -16.0
	credits_btn.add_theme_font_size_override("font_size", 22)
	credits_btn.add_theme_color_override("font_color", Color(0.55, 0.55, 0.55))
	credits_btn.pressed.connect(_on_credits)
	add_child(credits_btn)

	loading_label = Label.new()
	loading_label.text = "Loading..."
	loading_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	loading_label.set_anchors_preset(Control.PRESET_CENTER)
	loading_label.offset_left = -300.0
	loading_label.offset_right = 300.0
	loading_label.offset_top = 40.0
	loading_label.offset_bottom = 110.0
	loading_label.add_theme_font_size_override("font_size", 48)
	loading_label.visible = false
	add_child(loading_label)

	_build_settings()
	_build_credits()

	music = AudioStreamPlayer.new()
	music.stream = Assets.get_music("music_bgm")
	music.volume_db = -20.0
	add_child(music)
	if music.stream != null:
		music.play()


func _button(parent: Control, text: String, cb: Callable, min_size: Vector2 = Vector2(0, 76)) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = min_size
	b.add_theme_font_size_override("font_size", 44)
	b.pressed.connect(func(): Assets.play_2d("click", -5.0))
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


func _panel(w: float, h: float) -> Panel:
	var p := Panel.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -w * 0.5
	p.offset_right = w * 0.5
	p.offset_top = -h * 0.5
	p.offset_bottom = h * 0.5
	p.visible = false
	add_child(p)
	return p


func _build_settings() -> void:
	settings_panel = _panel(660, 360)
	var vb := VBoxContainer.new()
	vb.set_anchors_preset(Control.PRESET_FULL_RECT)
	vb.offset_left = 30.0
	vb.offset_right = -30.0
	vb.offset_top = 22.0
	vb.offset_bottom = -22.0
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	vb.add_theme_constant_override("separation", 18)
	settings_panel.add_child(vb)
	var t := Label.new()
	t.text = "SETTINGS"
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.add_theme_font_size_override("font_size", 52)
	vb.add_child(t)
	var s := Label.new()
	s.text = "LOOK SENSITIVITY"
	s.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.add_theme_font_size_override("font_size", 32)
	vb.add_child(s)
	var hb := HBoxContainer.new()
	hb.alignment = BoxContainer.ALIGNMENT_CENTER
	hb.add_theme_constant_override("separation", 16)
	vb.add_child(hb)
	_button(hb, "-", func(): _set_sens(Global.sensitivity - 0.1), Vector2(80, 70))
	sens_slider = HSlider.new()
	sens_slider.min_value = Global.MIN_SENS
	sens_slider.max_value = Global.MAX_SENS
	sens_slider.step = 0.1
	sens_slider.custom_minimum_size = Vector2(260, 60)
	sens_slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	sens_slider.value = Global.sensitivity
	sens_slider.value_changed.connect(func(v: float): _set_sens(v))
	hb.add_child(sens_slider)
	_button(hb, "+", func(): _set_sens(Global.sensitivity + 0.1), Vector2(80, 70))
	sens_label = Label.new()
	sens_label.text = "%.1f" % Global.sensitivity
	sens_label.custom_minimum_size = Vector2(70, 0)
	sens_label.add_theme_font_size_override("font_size", 40)
	hb.add_child(sens_label)
	_button(vb, "BACK", _close_panels, Vector2(0, 66))


func _build_credits() -> void:
	credits_panel = _panel(900, 600)
	var vb := VBoxContainer.new()
	vb.set_anchors_preset(Control.PRESET_FULL_RECT)
	vb.offset_left = 26.0
	vb.offset_right = -26.0
	vb.offset_top = 18.0
	vb.offset_bottom = -18.0
	vb.add_theme_constant_override("separation", 12)
	credits_panel.add_child(vb)
	var t := Label.new()
	t.text = "CREDITS"
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.add_theme_font_size_override("font_size", 44)
	vb.add_child(t)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	vb.add_child(scroll)
	var text := Label.new()
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.add_theme_font_size_override("font_size", 20)
	text.add_theme_font_override("font", ThemeDB.fallback_font)
	text.add_theme_constant_override("outline_size", 0)
	var body := "Game: Scary Aunty - MXYAN GAMES\nMade with Godot Engine (MIT licence).\n\n"
	if Assets.credits_text != "":
		body += Assets.credits_text
	else:
		body += "Asset credits are added when the game is built."
	text.text = body
	scroll.add_child(text)
	_button(vb, "BACK", _close_panels, Vector2(0, 62))


func _set_sens(v: float) -> void:
	Global.set_sensitivity(v)
	if absf(sens_slider.value - Global.sensitivity) > 0.001:
		sens_slider.set_value_no_signal(Global.sensitivity)
	sens_label.text = "%.1f" % Global.sensitivity


func _on_play() -> void:
	buttons.visible = false
	loading_label.visible = true
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().change_scene_to_file("res://scenes/game.tscn")


func _on_settings() -> void:
	_set_sens(Global.sensitivity)
	buttons.visible = false
	settings_panel.visible = true


func _on_credits() -> void:
	buttons.visible = false
	credits_panel.visible = true


func _close_panels() -> void:
	settings_panel.visible = false
	credits_panel.visible = false
	buttons.visible = true


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if settings_panel != null and (settings_panel.visible or credits_panel.visible):
			_close_panels()
		else:
			get_tree().quit()
