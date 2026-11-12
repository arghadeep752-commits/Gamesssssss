extends MenuScreen
## In-game shop (earned currency only): Characters, Skins, Weapons, Upgrades, Power-ups, Health.

const TABS := ["CHARACTERS", "SKINS", "WEAPONS", "UPGRADES", "POWER-UPS", "HEALTH"]

var tab := 0
var _list: VBoxContainer
var _tab_buttons: Array = []


func _ready() -> void:
	setup_screen("SHOP", 5)
	tab = int(SceneManager.params.get("tab", 0))
	var tabs_scroll := ScrollContainer.new()
	tabs_scroll.custom_minimum_size = Vector2(0, 92)
	tabs_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	content.add_child(tabs_scroll)
	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 8)
	tabs_scroll.add_child(tabs)
	for i in TABS.size():
		var b := UITheme.make_button(TABS[i], "grey", Vector2(0, 80), 24)
		b.custom_minimum_size = Vector2(190, 80)
		b.pressed.connect(func(): _select_tab(i))
		tabs.add_child(b)
		_tab_buttons.append(b)
	_list = scroll_area()
	_select_tab(tab)


func _select_tab(i: int) -> void:
	tab = i
	for j in _tab_buttons.size():
		var st := UITheme.button_styles("yellow" if j == i else "grey")
		for k in st:
			_tab_buttons[j].add_theme_stylebox_override(k, st[k])
	_rebuild()


func _rebuild() -> void:
	for c in _list.get_children():
		c.queue_free()
	match TABS[tab]:
		"CHARACTERS":
			for c in GameData.characters:
				if c.unlock_type != "default":
					_list.add_child(_character_card(c))
		"SKINS":
			for s in GameData.skins:
				_list.add_child(_skin_card(s))
		"WEAPONS":
			for w in GameData.weapons:
				if w.unlock_type != "default":
					_list.add_child(_weapon_card(w))
		"UPGRADES":
			for w in GameData.weapons:
				if SaveManager.owns_weapon(w.id):
					_list.add_child(_upgrade_card(w))
		"POWER-UPS":
			for p in GameData.powerups:
				if p.id != "health_recovery":
					_list.add_child(_powerup_card(p))
		"HEALTH":
			_list.add_child(_health_card())


func _card_shell(preview: Control, title: String, desc: String) -> Array:
	var panel := UITheme.make_panel("brown")
	panel.custom_minimum_size = Vector2(660, 0)
	panel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	panel.add_child(h)
	h.add_child(preview)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 6)
	h.add_child(v)
	v.add_child(UITheme.make_label(title, 32, Color(1, 0.86, 0.4), true, HORIZONTAL_ALIGNMENT_LEFT))
	var d := UITheme.make_label(desc, 22, Color(1, 0.96, 0.92), false, HORIZONTAL_ALIGNMENT_LEFT)
	d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	d.custom_minimum_size = Vector2(420, 0)
	v.add_child(d)
	return [panel, v]


func _icon_preview(tex: Texture2D, nearest := false, tint := Color.WHITE) -> Control:
	var bg := TextureRect.new()
	bg.texture = UITheme.tex("panels/round_grey_dark.png")
	bg.custom_minimum_size = Vector2(130, 130)
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	var ic := TextureRect.new()
	ic.texture = tex
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	ic.position = Vector2(22, 22)
	ic.size = Vector2(86, 86)
	ic.modulate = tint
	if nearest:
		ic.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	bg.add_child(ic)
	return bg


func _buy_button(v: VBoxContainer, text: String, color: String, enabled: bool, cb: Callable) -> void:
	var b := UITheme.make_button(text, color, Vector2(300, 82), 24)
	b.disabled = not enabled
	if enabled and cb.is_valid():
		b.pressed.connect(cb)
	v.add_child(b)


func _character_card(c: CharacterData) -> Control:
	var prev := make_ninja_preview(c, Vector2(130, 170), 1.15)
	var shell := _card_shell(prev, c.display_name.to_upper(), c.description + "\nSpecial: " + c.special_name)
	var v: VBoxContainer = shell[1]
	if SaveManager.is_character_unlocked(c.id):
		_buy_button(v, "OWNED", "grey", false, Callable())
	else:
		var done := func():
			SaveManager.unlock_character(c.id)
			_rebuild()
		_buy_button(v, price_text(c.price_coins, c.price_gems), "green", true, func(): try_purchase(c.display_name, c.price_coins, c.price_gems, done))
	return shell[0]


func _skin_card(s: SkinData) -> Control:
	var current := SaveManager.selected_character()
	var prev := make_ninja_preview(current, Vector2(130, 170), 1.15, "idle", s.id)
	var shell := _card_shell(prev, s.display_name.to_upper(), "Re-dyes %s's outfit. Equip on any unlocked ninja." % current.display_name)
	var v: VBoxContainer = shell[1]
	var equipped_id := SaveManager.equipped_skin(current.id)
	var is_eq := equipped_id == s.id or (equipped_id == "" and s.id == "original")
	if SaveManager.owns_skin(s.id):
		var eq := func():
			SaveManager.equip_skin(current.id, s.id)
			AudioManager.play_ui("menu_accept")
			_rebuild()
		_buy_button(v, "EQUIPPED" if is_eq else "EQUIP", "grey" if is_eq else "blue", not is_eq, eq)
	else:
		var done := func():
			SaveManager.add_skin(s.id)
			SaveManager.equip_skin(current.id, s.id)
			_rebuild()
		_buy_button(v, price_text(s.price_coins, s.price_gems), "green", true, func(): try_purchase(s.display_name + " skin", s.price_coins, s.price_gems, done))
	return shell[0]


func _weapon_card(w: WeaponData) -> Control:
	var shell := _card_shell(_icon_preview(w.icon, true), w.display_name.to_upper(), w.description + "\nAbility: " + w.ability_name)
	var v: VBoxContainer = shell[1]
	if SaveManager.owns_weapon(w.id):
		_buy_button(v, "OWNED", "grey", false, Callable())
	else:
		var done := func():
			SaveManager.add_weapon(w.id)
			_rebuild()
		_buy_button(v, price_text(w.price_coins, w.price_gems), "green", true, func(): try_purchase(w.display_name, w.price_coins, w.price_gems, done))
	return shell[0]


func _upgrade_card(w: WeaponData) -> Control:
	var lvl := SaveManager.weapon_level(w.id)
	var shell := _card_shell(_icon_preview(w.icon, true), "%s  LV %d" % [w.display_name.to_upper(), lvl], "Damage %d  ->  %d" % [int(w.damage_at(lvl)), int(w.damage_at(min(lvl + 1, w.max_level)))])
	var v: VBoxContainer = shell[1]
	if lvl >= w.max_level:
		_buy_button(v, "MAX LEVEL", "grey", false, Callable())
	else:
		var cost := w.upgrade_cost(lvl)
		var done := func():
			SaveManager.upgrade_weapon(w.id)
			_rebuild()
		_buy_button(v, "%d COINS" % cost, "yellow", true, func(): try_purchase("%s upgrade" % w.display_name, cost, 0, done))
	return shell[0]


func _powerup_card(p: PowerupData) -> Control:
	var count := SaveManager.consumable_count(p.id)
	var shell := _card_shell(_icon_preview(p.icon, false, p.color), p.display_name.to_upper(), p.description + "\nStart boost: activates automatically at the start of your next level.\nOwned: %d" % count)
	var v: VBoxContainer = shell[1]
	var done := func():
		SaveManager.add_consumable(p.id, 1)
		_rebuild()
	_buy_button(v, price_text(p.shop_price_coins, p.shop_price_gems), "green", count < 9, func(): try_purchase(p.display_name, p.shop_price_coins, p.shop_price_gems, done))
	return shell[0]


func _health_card() -> Control:
	var lvl := int(SaveManager.data.health_upgrades)
	var shell := _card_shell(_icon_preview(SpriteLib.tex("res://assets/ui/hud/hud_heart.png")), "MAX HEALTH  +%d" % (lvl * 20), "Each upgrade adds 20 maximum health to every ninja. (%d/5)" % lvl)
	var v: VBoxContainer = shell[1]
	if lvl >= 5:
		_buy_button(v, "MAXED", "grey", false, Callable())
	else:
		var cost := int(800 * pow(1.5, lvl))
		var done := func():
			SaveManager.data.health_upgrades = lvl + 1
			SaveManager.mark_dirty(true)
			_rebuild()
		_buy_button(v, "%d COINS" % cost, "red", true, func(): try_purchase("Health upgrade", cost, 0, done))
	return shell[0]


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
