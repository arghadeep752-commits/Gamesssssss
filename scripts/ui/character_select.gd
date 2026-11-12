extends MenuScreen
## Character selection carousel with animated preview, stats, special and unlock state.

var index := 0
var _preview_holder: Control
var _name: Label
var _desc: Label
var _special: Label
var _stats: VBoxContainer
var _action: Button
var _status: Label


func _ready() -> void:
	setup_screen("CHARACTERS", 2)
	var chars := GameData.characters
	for i in chars.size():
		if chars[i].id == SaveManager.data.selected_character:
			index = i
	var stage := HBoxContainer.new()
	stage.alignment = BoxContainer.ALIGNMENT_CENTER
	stage.add_theme_constant_override("separation", 10)
	content.add_child(stage)
	var left := UITheme.make_round_button(UITheme.tex("icons/gi_left.png"), "yellow", 100)
	left.pressed.connect(func(): _step(-1))
	stage.add_child(left)
	_preview_holder = Control.new()
	_preview_holder.custom_minimum_size = Vector2(380, 380)
	stage.add_child(_preview_holder)
	var right := UITheme.make_round_button(UITheme.tex("icons/gi_right.png"), "yellow", 100)
	right.pressed.connect(func(): _step(1))
	stage.add_child(right)
	_name = UITheme.make_title("", 60)
	content.add_child(_name)
	var panel := UITheme.make_panel("brown")
	content.add_child(panel)
	var pv := VBoxContainer.new()
	pv.add_theme_constant_override("separation", 10)
	panel.add_child(pv)
	_desc = UITheme.make_label("", 26, Color(1, 0.96, 0.9))
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.custom_minimum_size = Vector2(600, 0)
	pv.add_child(_desc)
	_stats = VBoxContainer.new()
	_stats.add_theme_constant_override("separation", 6)
	pv.add_child(_stats)
	_special = UITheme.make_label("", 24, Color(0.85, 0.75, 1))
	_special.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_special.custom_minimum_size = Vector2(600, 0)
	pv.add_child(_special)
	_status = UITheme.make_label("", 26, Color(1, 0.8, 0.5), true)
	content.add_child(_status)
	_action = UITheme.make_button("SELECT", "green", Vector2(480, 116), 42)
	_action.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_action.pressed.connect(_on_action)
	content.add_child(_action)
	_refresh(false)


func _step(d: int) -> void:
	index = (index + d + GameData.characters.size()) % GameData.characters.size()
	AudioManager.play_ui("menu_move")
	_refresh(true)


func _refresh(animate: bool) -> void:
	var c: CharacterData = GameData.characters[index]
	for ch in _preview_holder.get_children():
		ch.queue_free()
	var prev := make_ninja_preview(c, Vector2(380, 380), 2.6)
	_preview_holder.add_child(prev)
	if animate:
		prev.modulate.a = 0.0
		prev.position.x = 60.0
		var t := prev.create_tween().set_parallel(true)
		t.tween_property(prev, "modulate:a", 1.0, 0.2)
		t.tween_property(prev, "position:x", 0.0, 0.25).set_trans(Tween.TRANS_BACK)
	_name.text = c.display_name.to_upper()
	_name.add_theme_color_override("font_color", c.theme_color.lightened(0.35))
	_desc.text = c.description
	_special.text = "SPECIAL - %s: %s" % [c.special_name, c.special_description]
	for s in _stats.get_children():
		s.queue_free()
	_stat_row("Health", c.max_health / 140.0, "red")
	_stat_row("Speed", (c.move_speed - 250.0) / 160.0, "green")
	_stat_row("Power", c.damage_multiplier / 1.4, "blue")
	_stat_row("Jump", (c.jump_velocity - 880.0) / 140.0, "white")
	var unlocked := SaveManager.is_character_unlocked(c.id)
	var selected: bool = SaveManager.data.selected_character == c.id
	_action.disabled = false
	if selected:
		_action.text = "SELECTED"
		_action.disabled = true
		_status.text = ""
	elif unlocked:
		_action.text = "SELECT"
		_status.text = ""
	else:
		if c.price_coins > 0 or c.price_gems > 0:
			_action.text = "BUY  " + price_text(c.price_coins, c.price_gems)
		else:
			_action.text = "LOCKED"
			_action.disabled = true
		_status.text = "Unlocks free after level %d-%d" % [GameData.level(c.unlock_level).world, (c.unlock_level - 1) % 4 + 1] if c.unlock_level > 0 else "Available in the shop"


func _stat_row(label: String, ratio: float, color: String) -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 12)
	var l := UITheme.make_label(label, 24, Color.WHITE, true, HORIZONTAL_ALIGNMENT_LEFT)
	l.custom_minimum_size = Vector2(130, 0)
	h.add_child(l)
	var bar := UITheme.make_progress(color, Vector2(440, 28))
	bar.value = clampf(ratio, 0.08, 1.0) * 100.0
	h.add_child(bar)
	_stats.add_child(h)


func _on_action() -> void:
	var c: CharacterData = GameData.characters[index]
	if SaveManager.is_character_unlocked(c.id):
		SaveManager.select_character(c.id)
		AudioManager.play_ui("menu_accept")
		_celebrate()
		_refresh(false)
		return
	var done := func():
		SaveManager.unlock_character(c.id)
		SaveManager.select_character(c.id)
		_celebrate()
		_refresh(false)
	try_purchase(c.display_name, c.price_coins, c.price_gems, done)


func _celebrate() -> void:
	var prev: Control = _preview_holder.get_child(_preview_holder.get_child_count() - 1)
	var spr: AnimatedSprite2D = prev.get_node_or_null("Ninja")
	if spr:
		spr.play("jump_attack")
		spr.animation_finished.connect(func(): spr.play("idle"), CONNECT_ONE_SHOT)
	Effects.burst(self, _preview_holder.global_position + Vector2(190, 250), "star_04", Color(1, 0.9, 0.4), 18, 500.0, 0.8, 0.15, 400.0)


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
