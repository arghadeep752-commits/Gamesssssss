extends CanvasLayer
## SchoolBoy Runaway style HUD (same layout as the reference screenshot):
##   top-left: hint bulb       top-centre: chalk subtitles     top-right: pause
##   bottom-left: joystick     bottom-centre: 6 item slots      bottom-right: hand (use) button
## There is no crouch / stand button. Swipe anywhere else to look around.

const JOY_R := 88.0
const KNOB_R := 37.0
const HAND_R := 56.0
const SLOT := 82.0
const SLOT_GAP := 10.0
const KEY_COLORS := [Color(0.95, 0.22, 0.2), Color(0.35, 0.6, 1.0), Color(0.35, 0.92, 0.38), Color(1.0, 0.9, 0.3)]

var game
var root: Control
var draw_layer: Control
var subtitle: Label
var fade_rect: ColorRect
var red_rect: ColorRect
var dim: ColorRect
var _sub_tween: Tween

var joy_index := -1
var look_index := -1
var joy_vec := Vector2.ZERO
var hand_visible := false
var hand_text := ""
var modal_open := false
var _fps_t := 0.0
var _fps_text := "FPS 60"

var pause_panel: Panel
var settings_panel: Panel
var keypad_panel: Panel
var note_panel: Panel
var end_panel: Panel
var keypad_digits: Array = []
var keypad_labels: Array = []
var note_label: Label
var sens_label: Label
var sens_slider: HSlider
var end_title: Label
var end_info: Label
var _settings_from_pause := false


func setup(g) -> void:
	game = g
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	root = Control.new()
	root.name = "HudRoot"
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = Assets.get_theme()
	add_child(root)

	draw_layer = Control.new()
	draw_layer.name = "Controls"
	draw_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	draw_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	draw_layer.draw.connect(_on_draw)
	root.add_child(draw_layer)

	subtitle = Label.new()
	subtitle.name = "Subtitle"
	subtitle.anchor_left = 0.12
	subtitle.anchor_right = 0.88
	subtitle.offset_top = 34.0
	subtitle.offset_bottom = 150.0
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	subtitle.add_theme_font_size_override("font_size", 38)
	subtitle.add_theme_constant_override("outline_size", 10)
	subtitle.add_theme_color_override("font_outline_color", Color(0.05, 0.05, 0.05, 0.95))
	subtitle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	subtitle.modulate.a = 0.0
	root.add_child(subtitle)

	red_rect = _full_rect(Color(0.7, 0.0, 0.0, 0.0))
	dim = _full_rect(Color(0, 0, 0, 0.55))
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	dim.visible = false

	_build_pause()
	_build_settings()
	_build_keypad()
	_build_note()
	_build_end()
	fade_rect = _full_rect(Color(0, 0, 0, 1))


func _full_rect(col: Color) -> ColorRect:
	var r := ColorRect.new()
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.color = col
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(r)
	return r


# ================================================================ layout

func _vs() -> Vector2:
	return draw_layer.size


func joy_center() -> Vector2:
	return Vector2(150.0, _vs().y - 130.0)


func bulb_center() -> Vector2:
	return Vector2(60.0, 74.0)


func pause_center() -> Vector2:
	return Vector2(_vs().x - 64.0, 74.0)


func hand_center() -> Vector2:
	return Vector2(_vs().x - 140.0, _vs().y - 102.0)


func slot_rect(i: int) -> Rect2:
	var total := 6.0 * SLOT + 5.0 * SLOT_GAP
	var x0 := _vs().x * 0.5 - total * 0.5
	return Rect2(x0 + i * (SLOT + SLOT_GAP), _vs().y - 23.0 - SLOT, SLOT, SLOT)


func _controls_shown() -> bool:
	if modal_open or game == null:
		return false
	if fade_rect != null and fade_rect.color.a > 0.6:
		return false
	return game.state == "play" or game.state == "intro"


# ================================================================ drawing

func _process(delta: float) -> void:
	_fps_t -= delta
	if _fps_t <= 0.0:
		_fps_t = 0.5
		_fps_text = "FPS %d" % Engine.get_frames_per_second()
	draw_layer.queue_redraw()


func _on_draw() -> void:
	var vs := _vs()
	var small := ThemeDB.fallback_font
	draw_layer.draw_string(small, Vector2(12, 14), _fps_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1, 0.55))
	draw_layer.draw_string(small, Vector2(10, vs.y - 8), "0.1", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1, 0.4))
	if not _controls_shown():
		return
	var white := Color(1, 1, 1, 0.92)
	var dimc := Color(1, 1, 1, 0.42)

	# Joystick (white rings, like the screenshot)
	var jc := joy_center()
	draw_layer.draw_arc(jc, JOY_R, 0.0, TAU, 64, white, 3.0, true)
	var knob := jc + joy_vec * JOY_R
	draw_layer.draw_arc(knob, KNOB_R, 0.0, TAU, 48, white, 3.0, true)
	draw_layer.draw_arc(knob, KNOB_R - 9.0, deg_to_rad(110.0), deg_to_rad(250.0), 24, Color(1, 1, 1, 0.55), 2.0, true)

	# Hint bulb + pause
	_draw_bulb(bulb_center(), white)
	var pc := pause_center()
	draw_layer.draw_rect(Rect2(pc.x - 17.0, pc.y - 26.0, 9.0, 52.0), white)
	draw_layer.draw_rect(Rect2(pc.x + 8.0, pc.y - 26.0, 9.0, 52.0), white)

	# Inventory slots
	for i in range(6):
		var r := slot_rect(i)
		draw_layer.draw_rect(r, Color(0.07, 0.07, 0.07, 0.55))
		var sel: bool = i == game.selected
		var border := Color(1, 1, 1, 0.95) if sel else Color(0.62, 0.62, 0.62, 0.85)
		draw_layer.draw_rect(r, border, false, 3.0 if sel else 1.5)
		var item: String = game.inventory[i]
		if item != "":
			_draw_item_icon(item, r)

	# Hand (use) button
	var hc := hand_center()
	if hand_visible:
		draw_layer.draw_circle(hc, HAND_R, Color(0, 0, 0, 0.28))
		draw_layer.draw_arc(hc, HAND_R, 0.0, TAU, 64, white, 3.0, true)
		_draw_hand(hc, white)
		draw_layer.draw_string(Assets.chalk_font, hc + Vector2(-130.0, -HAND_R - 14.0), hand_text, HORIZONTAL_ALIGNMENT_CENTER, 260.0, 28, white)
	else:
		draw_layer.draw_arc(hc, HAND_R, 0.0, TAU, 64, dimc, 2.5, true)

	# Small aim dot in the middle
	var cc := vs * 0.5
	if hand_visible:
		draw_layer.draw_circle(cc, 5.0, Color(1, 1, 1, 0.85))
	else:
		draw_layer.draw_circle(cc, 2.5, Color(1, 1, 1, 0.5))


func _draw_bulb(c: Vector2, col: Color) -> void:
	var g := c + Vector2(0, -6)
	draw_layer.draw_arc(g, 15.0, deg_to_rad(135.0), deg_to_rad(405.0), 32, col, 3.0, true)
	draw_layer.draw_line(g + Vector2(-10.6, 10.6), g + Vector2(-7.0, 17.0), col, 3.0, true)
	draw_layer.draw_line(g + Vector2(10.6, 10.6), g + Vector2(7.0, 17.0), col, 3.0, true)
	draw_layer.draw_line(g + Vector2(-7.0, 18.0), g + Vector2(7.0, 18.0), col, 3.0, true)
	draw_layer.draw_line(g + Vector2(-6.0, 24.0), g + Vector2(6.0, 24.0), col, 3.0, true)
	draw_layer.draw_line(g + Vector2(-3.0, 29.0), g + Vector2(3.0, 29.0), col, 3.0, true)
	draw_layer.draw_polyline(PackedVector2Array([g + Vector2(-4, 12), g + Vector2(-4, 2), g + Vector2(0, 6), g + Vector2(4, 2), g + Vector2(4, 12)]), col, 2.0, true)
	for a in [-160.0, -125.0, -90.0, -55.0, -20.0]:
		var d := Vector2.from_angle(deg_to_rad(a))
		draw_layer.draw_line(g + d * 21.0, g + d * 29.0, col, 3.0, true)


func _draw_hand(c: Vector2, col: Color) -> void:
	draw_layer.draw_rect(Rect2(c.x - 15.0, c.y - 2.0, 30.0, 24.0), col, false, 3.0)
	for i in range(4):
		var x := c.x - 12.0 + i * 8.0
		var top := c.y - 26.0 + absf(i - 1.5) * 4.0
		draw_layer.draw_line(Vector2(x, c.y - 2.0), Vector2(x, top), col, 5.0, true)
		draw_layer.draw_circle(Vector2(x, top), 2.5, col)
	draw_layer.draw_line(Vector2(c.x - 15.0, c.y + 10.0), Vector2(c.x - 27.0, c.y - 4.0), col, 5.0, true)


func _draw_item_icon(item: String, r: Rect2) -> void:
	var c := r.get_center()
	var steel := Color(0.78, 0.78, 0.82)
	if item == "room_key" or item == "main_key":
		var kc := Color(1.0, 0.82, 0.3) if item == "main_key" else Color(0.85, 0.85, 0.92)
		draw_layer.draw_arc(c + Vector2(-16, 0), 10.0, 0.0, TAU, 24, kc, 4.0, true)
		draw_layer.draw_line(c + Vector2(-6, 0), c + Vector2(24, 0), kc, 5.0, true)
		draw_layer.draw_line(c + Vector2(15, 0), c + Vector2(15, 10), kc, 4.0, true)
		draw_layer.draw_line(c + Vector2(22, 0), c + Vector2(22, 8), kc, 4.0, true)
	elif item == "hammer":
		draw_layer.draw_line(c + Vector2(-22, 22), c + Vector2(8, -8), Color(0.72, 0.47, 0.26), 6.0, true)
		draw_layer.draw_colored_polygon(PackedVector2Array([c + Vector2(-2, -24), c + Vector2(24, 2), c + Vector2(17, 9), c + Vector2(-9, -17)]), steel)
	elif item == "bolt_cutter":
		var red := Color(0.88, 0.16, 0.1)
		draw_layer.draw_line(c + Vector2(-26, 12), c + Vector2(2, -2), red, 5.0, true)
		draw_layer.draw_line(c + Vector2(-26, 22), c + Vector2(4, 6), red, 5.0, true)
		draw_layer.draw_line(c + Vector2(2, -2), c + Vector2(24, -18), steel, 5.0, true)
		draw_layer.draw_line(c + Vector2(4, 6), c + Vector2(27, -9), steel, 5.0, true)


# ================================================================ touch input

func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var k := event as InputEventKey
		if k.pressed and not k.echo:
			_key(k.keycode)
		return
	if modal_open or game == null or not _controls_shown():
		if event is InputEventScreenTouch and not (event as InputEventScreenTouch).pressed:
			_touch_up((event as InputEventScreenTouch).index)
		return
	if event is InputEventScreenTouch:
		var st := event as InputEventScreenTouch
		if st.pressed:
			_touch_down(st.index, st.position)
		else:
			_touch_up(st.index)
	elif event is InputEventScreenDrag:
		var sd := event as InputEventScreenDrag
		if sd.index == joy_index:
			_update_joy(sd.position)
			get_viewport().set_input_as_handled()
		elif sd.index == look_index:
			game.player.look(sd.relative)
			get_viewport().set_input_as_handled()


func _key(code: int) -> void:
	if code == KEY_ESCAPE or code == KEY_P:
		if modal_open:
			_back()
		else:
			game.pause_game()
	elif modal_open:
		return
	elif code == KEY_E or code == KEY_F:
		game.interact()
	elif code >= KEY_1 and code <= KEY_6:
		game.select_slot(code - KEY_1)
	elif code == KEY_H:
		show_subtitle(game.get_hint(), 5.0, Color(1.0, 0.95, 0.6))


func _touch_down(index: int, pos: Vector2) -> void:
	if pos.distance_to(pause_center()) < 50.0:
		Assets.play_2d("click", -6.0)
		game.pause_game()
		get_viewport().set_input_as_handled()
		return
	if pos.distance_to(bulb_center()) < 52.0:
		Assets.play_2d("click", -6.0)
		show_subtitle(game.get_hint(), 5.5, Color(1.0, 0.95, 0.6))
		get_viewport().set_input_as_handled()
		return
	for i in range(6):
		if slot_rect(i).grow(4.0).has_point(pos):
			game.select_slot(i)
			get_viewport().set_input_as_handled()
			return
	if hand_visible and pos.distance_to(hand_center()) < HAND_R * 1.35:
		game.interact()
		get_viewport().set_input_as_handled()
		return
	if joy_index == -1 and pos.x < _vs().x * 0.42 and pos.y > _vs().y * 0.35:
		joy_index = index
		_update_joy(pos)
		get_viewport().set_input_as_handled()
		return
	if look_index == -1:
		look_index = index
		get_viewport().set_input_as_handled()


func _touch_up(index: int) -> void:
	if index == joy_index:
		joy_index = -1
		joy_vec = Vector2.ZERO
		if game != null and game.player != null:
			game.player.move_input = Vector2.ZERO
	if index == look_index:
		look_index = -1


func _update_joy(pos: Vector2) -> void:
	var v := (pos - joy_center()) / JOY_R
	if v.length() > 1.0:
		v = v.normalized()
	if v.length() < 0.12:
		v = Vector2.ZERO
	joy_vec = v
	game.player.move_input = Vector2(v.x, -v.y)


func release_touches() -> void:
	joy_index = -1
	look_index = -1
	joy_vec = Vector2.ZERO
	if game != null and game.player != null:
		game.player.move_input = Vector2.ZERO


func _notification(what: int) -> void:
	if game == null:
		return
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if modal_open:
			_back()
		else:
			game.pause_game()
	elif what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if not modal_open:
			game.pause_game()


# ================================================================ subtitles, hand, fades

func show_subtitle(text: String, duration: float = 2.5, col: Color = Color.WHITE) -> void:
	subtitle.text = text
	subtitle.add_theme_color_override("font_color", col)
	if _sub_tween != null and _sub_tween.is_valid():
		_sub_tween.kill()
	subtitle.modulate.a = 1.0
	_sub_tween = create_tween()
	_sub_tween.tween_interval(duration)
	_sub_tween.tween_property(subtitle, "modulate:a", 0.0, 0.5)


func set_hand(visible_now: bool, text: String) -> void:
	hand_visible = visible_now
	hand_text = text


func refresh_inventory() -> void:
	draw_layer.queue_redraw()


func fade_from_black(t: float) -> void:
	fade_rect.color.a = 1.0
	var tw := create_tween()
	tw.tween_property(fade_rect, "color:a", 0.0, t)


func fade_to_black(t: float) -> void:
	var tw := create_tween()
	tw.tween_property(fade_rect, "color:a", 1.0, t)


func flash_red() -> void:
	red_rect.color.a = 0.65
	var tw := create_tween()
	tw.tween_property(red_rect, "color:a", 0.0, 1.0)


# ================================================================ panels

func _panel(w: float, h: float) -> Panel:
	var p := Panel.new()
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.offset_left = -w * 0.5
	p.offset_right = w * 0.5
	p.offset_top = -h * 0.5
	p.offset_bottom = h * 0.5
	p.visible = false
	root.add_child(p)
	return p


func _vbox(parent: Control, sep: int = 14) -> VBoxContainer:
	var vb := VBoxContainer.new()
	vb.set_anchors_preset(Control.PRESET_FULL_RECT)
	vb.offset_left = 30.0
	vb.offset_right = -30.0
	vb.offset_top = 22.0
	vb.offset_bottom = -22.0
	vb.add_theme_constant_override("separation", sep)
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	parent.add_child(vb)
	return vb


func _label(parent: Control, text: String, font_size: int) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", font_size)
	parent.add_child(l)
	return l


func _button(parent: Control, text: String, cb: Callable, min_size: Vector2 = Vector2(0, 68)) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = min_size
	b.add_theme_font_size_override("font_size", 36)
	b.pressed.connect(func(): Assets.play_2d("click", -5.0))
	b.pressed.connect(cb)
	parent.add_child(b)
	return b


func _build_pause() -> void:
	pause_panel = _panel(460, 480)
	var vb := _vbox(pause_panel)
	_label(vb, "PAUSED", 56)
	_button(vb, "RESUME", _resume)
	_button(vb, "SETTINGS", _open_settings_from_pause)
	_button(vb, "RESTART", func(): game.restart())
	_button(vb, "MAIN MENU", func(): game.to_menu())


func _build_settings() -> void:
	settings_panel = _panel(660, 360)
	var vb := _vbox(settings_panel, 18)
	_label(vb, "SETTINGS", 52)
	_label(vb, "LOOK SENSITIVITY", 32)
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
	sens_label = _label(hb, "%.1f" % Global.sensitivity, 40)
	sens_label.custom_minimum_size = Vector2(70, 0)
	_button(vb, "BACK", _back)


func _set_sens(v: float) -> void:
	Global.set_sensitivity(v)
	if sens_slider != null and absf(sens_slider.value - Global.sensitivity) > 0.001:
		sens_slider.set_value_no_signal(Global.sensitivity)
	if sens_label != null:
		sens_label.text = "%.1f" % Global.sensitivity


func _build_keypad() -> void:
	keypad_panel = _panel(600, 660)
	var vb := _vbox(keypad_panel, 12)
	_label(vb, "AUNTY'S SAFE", 44)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 14)
	vb.add_child(row)
	for i in range(4):
		var box := PanelContainer.new()
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.02, 0.02, 0.02, 0.9)
		sb.border_color = KEY_COLORS[i]
		sb.set_border_width_all(5)
		sb.set_corner_radius_all(10)
		box.add_theme_stylebox_override("panel", sb)
		box.custom_minimum_size = Vector2(84, 92)
		row.add_child(box)
		var l := Label.new()
		l.text = "_"
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.add_theme_font_size_override("font_size", 60)
		box.add_child(l)
		keypad_labels.append(l)
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 10)
	vb.add_child(grid)
	for t in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]:
		var b := Button.new()
		b.text = t
		b.custom_minimum_size = Vector2(150, 70)
		b.add_theme_font_size_override("font_size", 40)
		b.pressed.connect(_on_key.bind(t))
		grid.add_child(b)
	_button(vb, "CLOSE", _back, Vector2(0, 62))


func _on_key(t: String) -> void:
	Assets.play_2d("beep", -6.0)
	if t == "C":
		keypad_digits.clear()
	elif t == "OK":
		if keypad_digits.size() == 4:
			if game.try_code(keypad_digits):
				keypad_digits.clear()
				_refresh_keypad()
				_close_all()
				return
			show_subtitle("Wrong code!", 1.6, Color(1, 0.4, 0.4))
			keypad_digits.clear()
	elif keypad_digits.size() < 4:
		keypad_digits.append(int(t))
	_refresh_keypad()


func _refresh_keypad() -> void:
	for i in range(4):
		var l: Label = keypad_labels[i]
		l.text = str(keypad_digits[i]) if i < keypad_digits.size() else "_"


func _build_note() -> void:
	note_panel = _panel(680, 560)
	var paper := StyleBoxFlat.new()
	paper.bg_color = Color(0.95, 0.92, 0.82)
	paper.border_color = Color(0.4, 0.3, 0.2)
	paper.set_border_width_all(3)
	paper.set_corner_radius_all(6)
	note_panel.add_theme_stylebox_override("panel", paper)
	var vb := _vbox(note_panel, 16)
	note_label = Label.new()
	note_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	note_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	note_label.add_theme_font_size_override("font_size", 32)
	note_label.add_theme_color_override("font_color", Color(0.15, 0.12, 0.1))
	note_label.add_theme_constant_override("outline_size", 0)
	vb.add_child(note_label)
	_button(vb, "CLOSE", _back, Vector2(0, 62))


func _build_end() -> void:
	end_panel = _panel(700, 430)
	var vb := _vbox(end_panel, 16)
	end_title = _label(vb, "", 64)
	end_info = _label(vb, "", 32)
	end_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_button(vb, "PLAY AGAIN", func(): game.restart())
	_button(vb, "MAIN MENU", func(): game.to_menu())


# ================================================================ opening / closing

func _show_only(p: Control) -> void:
	release_touches()
	for other in [pause_panel, settings_panel, keypad_panel, note_panel, end_panel]:
		other.visible = other == p
	dim.visible = true
	modal_open = true


func open_pause() -> void:
	_show_only(pause_panel)


func _open_settings_from_pause() -> void:
	_settings_from_pause = true
	_set_sens(Global.sensitivity)
	_show_only(settings_panel)


func open_keypad() -> void:
	keypad_digits.clear()
	_refresh_keypad()
	get_tree().paused = true
	_show_only(keypad_panel)


func open_note(text: String) -> void:
	note_label.text = text
	Assets.play_2d("paper", -2.0)
	get_tree().paused = true
	_show_only(note_panel)


func show_game_over() -> void:
	end_title.text = "AUNTY CAUGHT YOU!"
	end_title.add_theme_color_override("font_color", Color(1, 0.35, 0.3))
	end_info.text = "You have no chances left."
	_show_only(end_panel)
	fade_rect.color.a = 0.0


func show_win(seconds: float) -> void:
	end_title.text = "YOU ESCAPED!"
	end_title.add_theme_color_override("font_color", Color(0.5, 1.0, 0.5))
	end_info.text = "You escaped from Scary Aunty's house in %d min %02d sec!" % [int(seconds) / 60, int(seconds) % 60]
	_show_only(end_panel)


func _resume() -> void:
	_close_all()


func _close_all() -> void:
	for p in [pause_panel, settings_panel, keypad_panel, note_panel]:
		p.visible = false
	dim.visible = false
	modal_open = false
	get_tree().paused = false


## Back button / Escape / CLOSE / BACK.
func _back() -> void:
	if end_panel.visible:
		return
	if settings_panel.visible and _settings_from_pause:
		_settings_from_pause = false
		_show_only(pause_panel)
		return
	_close_all()
