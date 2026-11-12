extends MenuScreen
## Weapon inventory: equip, upgrade (levels 1-5), buy, unlock requirements.

var _list: VBoxContainer


func _ready() -> void:
	setup_screen("WEAPONS", 4)
	_list = scroll_area()
	_rebuild()


func _rebuild() -> void:
	for c in _list.get_children():
		c.queue_free()
	for w in GameData.weapons:
		_list.add_child(_card(w))


func _card(w: WeaponData) -> Control:
	var owned := SaveManager.owns_weapon(w.id)
	var equipped: bool = SaveManager.data.equipped_weapon == w.id
	var lvl := SaveManager.weapon_level(w.id)
	var panel := UITheme.make_panel("brown" if owned else "dark")
	panel.custom_minimum_size = Vector2(660, 0)
	panel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 18)
	panel.add_child(h)
	var icon_bg := TextureRect.new()
	icon_bg.texture = UITheme.tex("panels/round_grey_dark.png")
	icon_bg.custom_minimum_size = Vector2(130, 130)
	icon_bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	h.add_child(icon_bg)
	var icon := TextureRect.new()
	icon.texture = w.icon
	icon.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.position = Vector2(20, 20)
	icon.size = Vector2(90, 90)
	icon.rotation_degrees = -35 if w.kind == "melee" else 0
	icon.pivot_offset = Vector2(45, 45)
	icon_bg.add_child(icon)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 4)
	h.add_child(v)
	v.add_child(UITheme.make_label(w.display_name.to_upper(), 34, Color(1, 0.86, 0.4), true, HORIZONTAL_ALIGNMENT_LEFT))
	var d := UITheme.make_label(w.description, 22, Color(1, 0.96, 0.92), false, HORIZONTAL_ALIGNMENT_LEFT)
	d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	d.custom_minimum_size = Vector2(440, 0)
	v.add_child(d)
	var dmg_text := "Damage %d" % int(w.damage_at(lvl))
	if w.hits_per_attack > 1:
		dmg_text += " x%d" % w.hits_per_attack
	dmg_text += "   •   %s   •   Ability: %s" % ["Melee" if w.kind == "melee" else "Ranged", w.ability_name]
	v.add_child(UITheme.make_label(dmg_text, 20, Color(0.8, 0.9, 1), false, HORIZONTAL_ALIGNMENT_LEFT))
	var stars := HBoxContainer.new()
	v.add_child(stars)
	for i in w.max_level:
		var s := TextureRect.new()
		s.texture = UITheme.tex("buttons/yellow/star.png" if (owned and i < lvl) else "buttons/yellow/star_outline.png")
		s.custom_minimum_size = Vector2(34, 32)
		s.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		stars.add_child(s)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	v.add_child(row)
	if owned:
		var eq := UITheme.make_button("EQUIPPED" if equipped else "EQUIP", "green" if not equipped else "grey", Vector2(200, 80), 26)
		eq.disabled = equipped
		eq.pressed.connect(func():
			SaveManager.equip_weapon(w.id)
			AudioManager.play_ui("menu_accept")
			_rebuild())
		row.add_child(eq)
		if lvl < w.max_level:
			var cost := w.upgrade_cost(lvl)
			var up := UITheme.make_button("UPGRADE %d" % cost, "yellow", Vector2(250, 80), 24)
			up.pressed.connect(_upgrade.bind(w, lvl, cost))
			row.add_child(up)
		else:
			row.add_child(UITheme.make_label("MAX LEVEL", 24, Color(1, 0.85, 0.3), true))
	else:
		if w.price_coins > 0 or w.price_gems > 0:
			var buy := UITheme.make_button("BUY " + price_text(w.price_coins, w.price_gems), "red", Vector2(300, 80), 24)
			buy.pressed.connect(_buy.bind(w))
			row.add_child(buy)
		if w.unlock_level > 0:
			var lvl_req := GameData.level(w.unlock_level)
			row.add_child(UITheme.make_label("or clear %d-%d" % [lvl_req.world, (w.unlock_level - 1) % 4 + 1], 20, Color(0.9, 0.8, 1), false))
	return panel


func _upgrade(w: WeaponData, lvl: int, cost: int) -> void:
	var done := func():
		SaveManager.upgrade_weapon(w.id)
		_rebuild()
	try_purchase("%s level %d" % [w.display_name, lvl + 1], cost, 0, done)


func _buy(w: WeaponData) -> void:
	var done := func():
		SaveManager.add_weapon(w.id)
		_rebuild()
	try_purchase(w.display_name, w.price_coins, w.price_gems, done)


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
