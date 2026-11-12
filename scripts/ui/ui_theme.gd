extends Node
## Shared UI kit built on Kenney's CC0 UI packs: theme, fonts and widget factories
## so every screen looks consistent.

const UI := "res://assets/ui/"

var font_bold: FontFile
var font_body: FontFile
var font_title: FontFile
var theme: Theme

const COLORS := {
	"gold": Color(1.0, 0.82, 0.28),
	"text": Color(1, 1, 1),
	"muted": Color(0.82, 0.80, 0.90),
	"danger": Color(1.0, 0.36, 0.32),
	"good": Color(0.45, 0.95, 0.55),
	"ink": Color(0.10, 0.07, 0.14),
	"panel": Color(0.13, 0.10, 0.20, 0.92),
}


func _ready() -> void:
	font_bold = load("res://fonts/Kenney_Future.ttf")
	font_body = load("res://fonts/Kenney_Future_Narrow.ttf")
	font_title = load("res://fonts/Kenney_Future.ttf")
	theme = _build_theme()


## Top inset (in viewport pixels) for phones with notches / punch-hole cameras.
func safe_top() -> float:
	var screen := DisplayServer.screen_get_size()
	var safe := DisplayServer.get_display_safe_area()
	if screen.y <= 0 or safe.size.y <= 0:
		return 0.0
	var vp_h := get_viewport().get_visible_rect().size.y
	return clampf(float(safe.position.y) * vp_h / float(screen.y), 0.0, 120.0)


func tex(rel: String) -> Texture2D:
	return SpriteLib.tex(UI + rel)


func _box(rel: String, margins: Array, content := Vector4(16, 12, 16, 12)) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = tex(rel)
	sb.texture_margin_left = margins[0]
	sb.texture_margin_top = margins[1]
	sb.texture_margin_right = margins[2]
	sb.texture_margin_bottom = margins[3]
	sb.content_margin_left = content.x
	sb.content_margin_top = content.y
	sb.content_margin_right = content.z
	sb.content_margin_bottom = content.w
	return sb


func button_styles(color: String) -> Dictionary:
	var c := color.to_lower()
	var normal := _box("buttons/%s/button_rectangle_depth_gloss.png" % c, [26, 22, 26, 30], Vector4(24, 10, 24, 22))
	var pressed := _box("buttons/%s/button_rectangle_gloss.png" % c, [26, 22, 26, 22], Vector4(24, 18, 24, 14))
	var disabled := _box("buttons/grey/button_rectangle_depth_flat.png", [26, 22, 26, 30], Vector4(24, 10, 24, 22))
	return {"normal": normal, "hover": normal, "pressed": pressed, "disabled": disabled, "focus": StyleBoxEmpty.new()}


func _build_theme() -> Theme:
	var t := Theme.new()
	t.default_font = font_body
	t.default_font_size = 30
	var bs := button_styles("blue")
	for k in bs:
		t.set_stylebox(k, "Button", bs[k])
	t.set_font("font", "Button", font_bold)
	t.set_font_size("font_size", "Button", 36)
	t.set_color("font_color", "Button", Color.WHITE)
	t.set_color("font_pressed_color", "Button", Color(0.92, 0.92, 0.92))
	t.set_color("font_hover_color", "Button", Color.WHITE)
	t.set_color("font_disabled_color", "Button", Color(0.75, 0.75, 0.75))
	t.set_color("font_outline_color", "Button", Color(0, 0, 0, 0.55))
	t.set_constant("outline_size", "Button", 6)
	t.set_constant("icon_max_width", "Button", 56)
	t.set_color("font_color", "Label", Color.WHITE)
	t.set_color("font_outline_color", "Label", Color(0.05, 0.03, 0.08, 0.9))
	t.set_constant("outline_size", "Label", 8)
	t.set_color("font_shadow_color", "Label", Color(0, 0, 0, 0.35))
	t.set_constant("shadow_offset_y", "Label", 3)
	t.set_stylebox("panel", "PanelContainer", panel_style("brown"))
	t.set_stylebox("panel", "Panel", panel_style("brown"))
	# slider
	var track := _box("buttons/grey/slide_horizontal_grey.png", [16, 0, 16, 0], Vector4(0, 12, 0, 12))
	var fill := _box("buttons/yellow/slide_horizontal_color.png", [16, 0, 16, 0], Vector4(0, 12, 0, 12))
	t.set_stylebox("slider", "HSlider", track)
	t.set_stylebox("grabber_area", "HSlider", fill)
	t.set_stylebox("grabber_area_highlight", "HSlider", fill)
	t.set_icon("grabber", "HSlider", tex("buttons/yellow/slide_hangle.png"))
	t.set_icon("grabber_highlight", "HSlider", tex("buttons/yellow/slide_hangle.png"))
	t.set_icon("checked", "CheckBox", tex("buttons/green/check_square_color_checkmark.png"))
	t.set_icon("unchecked", "CheckBox", tex("buttons/grey/check_square_grey.png"))
	t.set_font("font", "CheckBox", font_body)
	t.set_font_size("font_size", "CheckBox", 30)
	for k in ["normal", "hover", "pressed", "focus", "hover_pressed"]:
		t.set_stylebox(k, "CheckBox", StyleBoxEmpty.new())
	var scroll := StyleBoxFlat.new()
	scroll.bg_color = Color(1, 1, 1, 0.08)
	scroll.set_corner_radius_all(6)
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(1, 0.82, 0.3, 0.6)
	grab.set_corner_radius_all(6)
	t.set_stylebox("scroll", "VScrollBar", scroll)
	t.set_stylebox("grabber", "VScrollBar", grab)
	t.set_stylebox("grabber_highlight", "VScrollBar", grab)
	t.set_stylebox("grabber_pressed", "VScrollBar", grab)
	return t


func panel_style(kind := "brown") -> StyleBoxTexture:
	var path := "panels/panel_brown.png"
	match kind:
		"dark":
			path = "panels/panel_brown_dark.png"
		"grey":
			path = "panels/panel_grey_dark.png"
		"corners":
			path = "panels/panel_brown_corners_a.png"
		"border":
			path = "panels/panel_border_brown.png"
	return _box(path, [36, 36, 36, 36], Vector4(28, 24, 28, 24))


# ------------------------------------------------------------- factories
func make_label(text: String, size := 30, color := Color.WHITE, bold := false, align := HORIZONTAL_ALIGNMENT_CENTER) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", font_bold if bold else font_body)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.05, 0.03, 0.08, 0.95))
	l.add_theme_constant_override("outline_size", max(4, int(size / 5.0)))
	return l


func make_title(text: String, size := 64, color := Color(1, 0.85, 0.3)) -> Label:
	var l := make_label(text, size, color, true)
	l.add_theme_constant_override("outline_size", int(size / 4.0))
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.5))
	l.add_theme_constant_override("shadow_offset_y", 6)
	return l


func make_button(text: String, color := "blue", min_size := Vector2(440, 112), font_size := 38, icon: Texture2D = null) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = min_size
	b.focus_mode = Control.FOCUS_NONE
	var st := button_styles(color)
	for k in st:
		b.add_theme_stylebox_override(k, st[k])
	b.add_theme_font_size_override("font_size", font_size)
	if icon:
		b.icon = icon
		b.expand_icon = false
		b.add_theme_constant_override("icon_max_width", int(min_size.y * 0.5))
	_add_press_feel(b)
	return b


func make_round_button(icon: Texture2D, color := "blue", size := 96.0) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(size, size)
	b.focus_mode = Control.FOCUS_NONE
	var n := _box("buttons/%s/button_round_depth_gloss.png" % color, [40, 40, 40, 46], Vector4(10, 8, 10, 16))
	var p := _box("buttons/%s/button_round_gloss.png" % color, [40, 40, 40, 40], Vector4(10, 14, 10, 10))
	b.add_theme_stylebox_override("normal", n)
	b.add_theme_stylebox_override("hover", n)
	b.add_theme_stylebox_override("pressed", p)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.icon = icon
	b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	b.expand_icon = true
	_add_press_feel(b)
	return b


func make_square_button(color := "blue", size := Vector2(150, 150)) -> Button:
	var b := Button.new()
	b.custom_minimum_size = size
	b.focus_mode = Control.FOCUS_NONE
	var n := _box("buttons/%s/button_square_depth_gloss.png" % color, [30, 30, 30, 38], Vector4(8, 6, 8, 14))
	var p := _box("buttons/%s/button_square_gloss.png" % color, [30, 30, 30, 30], Vector4(8, 12, 8, 8))
	b.add_theme_stylebox_override("normal", n)
	b.add_theme_stylebox_override("hover", n)
	b.add_theme_stylebox_override("pressed", p)
	b.add_theme_stylebox_override("disabled", _box("buttons/grey/button_square_depth_gloss.png", [30, 30, 30, 38], Vector4(8, 6, 8, 14)))
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_add_press_feel(b)
	return b


func _add_press_feel(b: Button) -> void:
	b.pivot_offset = b.custom_minimum_size / 2.0
	b.resized.connect(func(): b.pivot_offset = b.size / 2.0)
	b.button_down.connect(func():
		var t := b.create_tween()
		t.tween_property(b, "scale", Vector2(0.94, 0.94), 0.06)
		Haptics.light())
	b.button_up.connect(func():
		var t := b.create_tween()
		t.tween_property(b, "scale", Vector2(1.0, 1.0), 0.12).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT))
	b.pressed.connect(func(): AudioManager.play_ui("click"))


func make_panel(kind := "brown") -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", panel_style(kind))
	return p


func make_progress(color := "red", size := Vector2(300, 36)) -> TextureProgressBar:
	var bar := TextureProgressBar.new()
	bar.nine_patch_stretch = true
	bar.stretch_margin_left = 14
	bar.stretch_margin_right = 14
	bar.stretch_margin_top = 12
	bar.stretch_margin_bottom = 12
	bar.texture_under = tex("panels/progress_transparent.png")
	bar.texture_progress = tex("panels/progress_%s.png" % color)
	bar.custom_minimum_size = size
	bar.min_value = 0
	bar.max_value = 100
	bar.value = 100
	bar.tint_under = Color(0.1, 0.06, 0.12, 0.85)
	return bar


func make_slider(value: float) -> HSlider:
	var s := HSlider.new()
	s.min_value = 0.0
	s.max_value = 1.0
	s.step = 0.05
	s.value = value
	s.custom_minimum_size = Vector2(320, 48)
	s.focus_mode = Control.FOCUS_NONE
	return s


func icon(name: String) -> Texture2D:
	return tex("icons/%s.png" % name)


func make_currency_bar() -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 14)
	var coin_box := _currency_chip("res://assets/ui/hud/hud_coin.png", "coins")
	var gem_box := _currency_chip("res://assets/environments/props/gem_blue.png", "gems")
	h.add_child(coin_box)
	h.add_child(gem_box)
	var update := func():
		if is_instance_valid(coin_box):
			(coin_box.find_child("Value", true, false) as Label).text = str(SaveManager.coins())
			(gem_box.find_child("Value", true, false) as Label).text = str(SaveManager.gems())
	Events.currency_changed.connect(update)
	h.tree_exiting.connect(func(): Events.currency_changed.disconnect(update))
	update.call()
	return h


func _currency_chip(icon_path: String, id: String) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.03, 0.10, 0.7)
	sb.set_corner_radius_all(28)
	sb.content_margin_left = 10
	sb.content_margin_right = 22
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	p.add_theme_stylebox_override("panel", sb)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	p.add_child(h)
	var ic := TextureRect.new()
	ic.texture = SpriteLib.tex(icon_path)
	ic.custom_minimum_size = Vector2(48, 48)
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	h.add_child(ic)
	var l := make_label("0", 32, Color.WHITE, true)
	l.name = "Value"
	l.custom_minimum_size = Vector2(90, 0)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	h.add_child(l)
	return p


## Modal dialog. buttons: Array of [text, color, Callable]
func popup(parent: Node, title: String, body: String, buttons: Array) -> Control:
	var layer := Control.new()
	layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.mouse_filter = Control.MOUSE_FILTER_STOP
	layer.z_index = 50
	parent.add_child(layer)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(center)
	var panel := make_panel("brown")
	panel.custom_minimum_size = Vector2(600, 0)
	center.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 22)
	panel.add_child(v)
	v.add_child(make_title(title, 44))
	var msg := make_label(body, 28, Color(1, 0.96, 0.9))
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	msg.custom_minimum_size = Vector2(520, 0)
	v.add_child(msg)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 18)
	v.add_child(row)
	for spec in buttons:
		var b := make_button(spec[0], spec[1], Vector2(250, 96), 30)
		var cb: Callable = spec[2]
		b.pressed.connect(func():
			layer.queue_free()
			if cb.is_valid():
				cb.call())
		row.add_child(b)
	panel.pivot_offset = Vector2(300, 150)
	panel.scale = Vector2(0.7, 0.7)
	panel.modulate.a = 0.0
	var t := panel.create_tween().set_parallel(true)
	t.tween_property(panel, "scale", Vector2.ONE, 0.22).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_property(panel, "modulate:a", 1.0, 0.15)
	AudioManager.play_ui("pop")
	return layer


func toast(parent: Node, text: String, color := Color(1, 0.85, 0.3)) -> void:
	var l := make_label(text, 34, color, true)
	l.set_anchors_preset(Control.PRESET_CENTER_TOP)
	l.position = Vector2(-340, 170)
	l.size = Vector2(680, 60)
	l.z_index = 60
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	l.modulate.a = 0.0
	var t := l.create_tween()
	t.tween_property(l, "modulate:a", 1.0, 0.2)
	t.parallel().tween_property(l, "position:y", 150.0, 0.2)
	t.tween_interval(1.6)
	t.tween_property(l, "modulate:a", 0.0, 0.4)
	t.tween_callback(l.queue_free)


## Slides / fades a freshly built screen in.
func animate_in(root: Control) -> void:
	var i := 0
	for c in root.find_children("*", "Button", true, false):
		var b: Button = c
		b.modulate.a = 0.0
		var t := b.create_tween()
		t.tween_interval(0.04 * i)
		t.tween_property(b, "modulate:a", 1.0, 0.25)
		i += 1


func back_button(on_press: Callable) -> Button:
	var b := make_round_button(tex("icons/gi_return.png"), "red", 100)
	b.pressed.connect(on_press)
	return b
