class_name MenuScreen
extends Control
## Base for menu screens: animated themed background, header with back button + currency.

var content: VBoxContainer
var _bg_layers: Array = []
var _world_theme := 1


func setup_screen(title: String, world_theme := 1, show_back := true, back_target := "res://scenes/menus/main_menu.tscn") -> void:
	theme = UITheme.theme
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_world_theme = world_theme
	_build_background(world_theme)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_top", 30 + int(UITheme.safe_top()))
	margin.add_theme_constant_override("margin_bottom", 24)
	add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 14)
	margin.add_child(root)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	root.add_child(header)
	if show_back:
		var back := UITheme.back_button(func(): SceneManager.goto_menu(back_target, _back_params()))
		header.add_child(back)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	header.add_child(UITheme.make_currency_bar())
	if title != "":
		var t := UITheme.make_title(title, 56)
		root.add_child(t)
	content = VBoxContainer.new()
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_theme_constant_override("separation", 14)
	root.add_child(content)


func _back_params() -> Dictionary:
	return {}


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		_on_back_key()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		_on_back_key()


func _on_back_key() -> void:
	pass


func _build_background(world_id: int) -> void:
	var w := GameData.world(world_id)
	var sky := ColorRect.new()
	sky.set_anchors_preset(Control.PRESET_FULL_RECT)
	sky.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := ShaderMaterial.new()
	m.shader = preload("res://shaders/sky_gradient.gdshader")
	m.set_shader_parameter("top_color", w.sky_top)
	m.set_shader_parameter("bottom_color", w.sky_bottom)
	sky.material = m
	add_child(sky)
	var bands := [["background_fade_%s.png" % w.bg, 0.62, Color(w.layer_tint).lightened(0.25), 8.0], ["background_color_%s.png" % w.bg, 0.72, w.layer_tint, 16.0]]
	for b in bands:
		var tex := SpriteLib.tex("res://assets/backgrounds/" + b[0])
		if tex == null:
			continue
		var tr := TextureRect.new()
		tr.texture = tex
		tr.stretch_mode = TextureRect.STRETCH_TILE
		tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
		tr.modulate = b[2]
		tr.anchor_top = b[1]
		tr.anchor_bottom = b[1]
		tr.anchor_right = 0.0
		tr.position = Vector2(0, -tex.get_height() * 3.0 * 0.5)
		tr.scale = Vector2(3, 3)
		tr.size = Vector2(1400, tex.get_height())
		add_child(tr)
		_bg_layers.append([tr, b[3], tex.get_width() * 3.0])
		var fill := ColorRect.new()
		fill.color = Color(b[2]).darkened(0.3) * Color(w.sky_bottom).darkened(0.15)
		fill.anchor_top = b[1]
		fill.anchor_bottom = 1.0
		fill.anchor_right = 1.0
		fill.offset_top = tex.get_height() * 3.0 * 0.5 - 6
		fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(fill)
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0.02, 0.0, 0.06, 0.25)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	if int(SaveManager.setting("quality")) > 0:
		var p := CPUParticles2D.new()
		p.amount = 22
		p.lifetime = 9.0
		p.preprocess = 6.0
		p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
		p.emission_rect_extents = Vector2(420, 10)
		p.position = Vector2(360, -30)
		p.direction = Vector2(-0.3, 1)
		p.spread = 20
		p.gravity = Vector2(0, 20)
		p.initial_velocity_min = 30
		p.initial_velocity_max = 80
		p.angular_velocity_min = -80
		p.angular_velocity_max = 80
		p.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		var at := AtlasTexture.new()
		at.atlas = SpriteLib.tex("res://assets/effects/pixel/%s.png" % ("leaf_pink" if world_id != 3 else "snow"))
		at.region = Rect2(0, 0, 12 if world_id != 3 else 8, at.atlas.get_height())
		p.texture = at
		p.scale_amount_min = 2.5
		p.scale_amount_max = 3.5
		add_child(p)


func _process(delta: float) -> void:
	for l in _bg_layers:
		var tr: TextureRect = l[0]
		tr.position.x -= l[1] * delta
		if tr.position.x < -l[2]:
			tr.position.x += l[2]


## Ninja preview sprite inside UI (AnimatedSprite2D hosted by a Control).
func make_ninja_preview(character: CharacterData, size := Vector2(260, 300), sc := 2.0, anim := "idle", skin_id := "") -> Control:
	var holder := Control.new()
	holder.custom_minimum_size = size
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var spr := AnimatedSprite2D.new()
	spr.name = "Ninja"
	spr.sprite_frames = SpriteLib.ninja_frames()
	spr.scale = Vector2(sc, sc)
	var ch := SpriteLib.ninja_cell_height()
	spr.offset = Vector2(0, -(ch / 2.0 - SpriteLib.ninja_foot_margin()))
	spr.position = Vector2(size.x / 2.0, size.y - 10)
	if skin_id != "":
		var s := GameData.skin(skin_id)
		if s.id == "original":
			spr.material = SpriteLib.make_fx_material(character.cloth_hue, character.cloth_saturation, character.cloth_value, character.armor_tint)
		else:
			spr.material = SpriteLib.make_fx_material(s.cloth_hue, s.cloth_saturation, s.cloth_value, s.armor_tint)
	else:
		spr.material = SpriteLib.material_for_character(character)
	spr.play(anim)
	holder.add_child(spr)
	var shadow := Sprite2D.new()
	shadow.texture = SpriteLib.tex("res://assets/effects/circle_05.png")
	shadow.modulate = Color(0, 0, 0, 0.35)
	shadow.scale = Vector2(0.5 * sc / 2.0, 0.1 * sc / 2.0)
	shadow.position = spr.position + Vector2(0, -4)
	holder.add_child(shadow)
	holder.move_child(shadow, 0)
	return holder


func scroll_area() -> VBoxContainer:
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	content.add_child(sc)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 16)
	sc.add_child(v)
	return v


func price_text(coins: int, gems: int) -> String:
	if gems > 0 and coins > 0:
		return "%d  +  %d gems" % [coins, gems]
	if gems > 0:
		return "%d GEMS" % gems
	return "%d COINS" % coins


## Generic purchase flow with confirmation / insufficient funds messages.
func try_purchase(item_name: String, coins: int, gems: int, on_success: Callable) -> void:
	if not SaveManager.can_afford(coins, gems):
		AudioManager.play_ui("error")
		var need := []
		if SaveManager.coins() < coins:
			need.append("%d more coins" % (coins - SaveManager.coins()))
		if SaveManager.gems() < gems:
			need.append("%d more gems" % (gems - SaveManager.gems()))
		UITheme.popup(self, "NOT ENOUGH", "You need %s to buy %s.\nPlay levels and open chests to earn more!" % [" and ".join(need), item_name], [["OK", "blue", Callable()]])
		return
	var buy := func():
		if SaveManager.spend(coins, gems):
			AudioManager.play_ui("purchase")
			AudioManager.play_ui("unlock")
			Haptics.medium()
			_purchase_fx()
			on_success.call()
	UITheme.popup(self, "CONFIRM", "Buy %s for %s?" % [item_name, price_text(coins, gems)], [["CANCEL", "red", Callable()], ["BUY", "green", buy]])


func _purchase_fx() -> void:
	var vp := get_viewport_rect().size
	var p := CPUParticles2D.new()
	p.texture = SpriteLib.tex("res://assets/environments/props/coin_gold.png")
	p.one_shot = true
	p.explosiveness = 0.9
	p.amount = 24
	p.lifetime = 1.0
	p.spread = 180
	p.initial_velocity_min = 300
	p.initial_velocity_max = 700
	p.gravity = Vector2(0, 1400)
	p.scale_amount_min = 0.5
	p.scale_amount_max = 0.8
	p.position = vp / 2.0
	p.z_index = 70
	add_child(p)
	p.emitting = true
	p.finished.connect(p.queue_free)
	UITheme.toast(self, "PURCHASED!", Color(0.5, 1, 0.6))
