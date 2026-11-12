class_name HUD
extends CanvasLayer
## Gameplay HUD: portrait, health/energy, lives, coins, gems, power-up timers, boss bar.

signal pause_pressed

var _hp: TextureProgressBar
var _hp_ghost: TextureProgressBar
var _energy: TextureProgressBar
var _coins: Label
var _gems: Label
var _lives: Label
var _powerups: HBoxContainer
var _boss_box: VBoxContainer
var _boss_bar: TextureProgressBar
var _boss_name: Label
var _title: Label
var _special_ready: Label
var _pu_items := {}
var _root: Control
var _fps: Label


func _ready() -> void:
	layer = 10
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UITheme.theme
	add_child(_root)
	offset = Vector2(0, UITheme.safe_top())
	_build_left()
	_build_right()
	_build_boss()
	_title = UITheme.make_title("", 46)
	_title.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_title.position = Vector2(-340, 300)
	_title.size = Vector2(680, 120)
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.modulate.a = 0.0
	_root.add_child(_title)
	_fps = UITheme.make_label("", 20, Color(0.7, 1, 0.7))
	_fps.position = Vector2(12, 250)
	_fps.visible = bool(SaveManager.setting("show_fps"))
	_root.add_child(_fps)
	Events.player_health_changed.connect(_on_health)
	Events.player_energy_changed.connect(_on_energy)
	Events.player_lives_changed.connect(func(l): _lives.text = "x%d" % l)
	Events.level_coins_changed.connect(_on_level_coins)
	Events.gems_changed.connect(_on_gems)
	Events.powerup_started.connect(_on_powerup)
	Events.powerup_ended.connect(_on_powerup_end)
	Events.boss_started.connect(_on_boss_started)
	Events.boss_health_changed.connect(_on_boss_hp)
	Events.boss_defeated.connect(func(_id): _hide_boss())
	Events.toast.connect(func(t, c): UITheme.toast(_root, t, c))


func _process(delta: float) -> void:
	if _hp_ghost.value > _hp.value:
		_hp_ghost.value = move_toward(_hp_ghost.value, _hp.value, 60.0 * delta)
	else:
		_hp_ghost.value = _hp.value
	for id in _pu_items.keys():
		var item: Dictionary = _pu_items[id]
		item.left -= delta
		item.bar.value = max(0.0, item.left / item.total * 100.0)
	if _fps.visible:
		_fps.text = "%d FPS" % Engine.get_frames_per_second()


func _build_left() -> void:
	var box := HBoxContainer.new()
	box.position = Vector2(16, 26)
	box.add_theme_constant_override("separation", 10)
	_root.add_child(box)
	var frame := TextureRect.new()
	frame.texture = UITheme.tex("panels/round_brown.png")
	frame.custom_minimum_size = Vector2(104, 104)
	frame.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	box.add_child(frame)
	var portrait := TextureRect.new()
	var at := AtlasTexture.new()
	at.atlas = SpriteLib.tex("res://assets/characters/ninja/idle.png")
	at.region = Rect2(2, 6, 66, 62)
	portrait.texture = at
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait.position = Vector2(12, 10)
	portrait.size = Vector2(80, 80)
	portrait.material = SpriteLib.material_for_character(SaveManager.selected_character())
	frame.add_child(portrait)
	var bars := VBoxContainer.new()
	bars.add_theme_constant_override("separation", 6)
	box.add_child(bars)
	var hp_stack := Control.new()
	hp_stack.custom_minimum_size = Vector2(250, 38)
	bars.add_child(hp_stack)
	_hp_ghost = UITheme.make_progress("white", Vector2(250, 38))
	_hp_ghost.tint_progress = Color(1, 0.85, 0.6, 0.8)
	hp_stack.add_child(_hp_ghost)
	_hp = UITheme.make_progress("red", Vector2(250, 38))
	_hp.texture_under = null
	hp_stack.add_child(_hp)
	_energy = UITheme.make_progress("blue", Vector2(200, 26))
	_energy.value = 0
	bars.add_child(_energy)
	var lives_row := HBoxContainer.new()
	lives_row.add_theme_constant_override("separation", 4)
	bars.add_child(lives_row)
	var heart := TextureRect.new()
	heart.texture = SpriteLib.tex("res://assets/ui/hud/hud_heart.png")
	heart.custom_minimum_size = Vector2(34, 34)
	heart.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	lives_row.add_child(heart)
	_lives = UITheme.make_label("x3", 26, Color.WHITE, true)
	lives_row.add_child(_lives)
	_special_ready = UITheme.make_label("SPECIAL READY", 20, Color(0.75, 0.85, 1), true)
	_special_ready.visible = false
	lives_row.add_child(_special_ready)
	_powerups = HBoxContainer.new()
	_powerups.position = Vector2(20, 168)
	_powerups.add_theme_constant_override("separation", 8)
	_root.add_child(_powerups)


func _build_right() -> void:
	var box := HBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	box.position = Vector2(-420, 26)
	box.size = Vector2(404, 90)
	box.alignment = BoxContainer.ALIGNMENT_END
	box.add_theme_constant_override("separation", 10)
	_root.add_child(box)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	box.add_child(v)
	_coins = _counter(v, "res://assets/ui/hud/hud_coin.png")
	_gems = _counter(v, "res://assets/environments/props/gem_blue.png")
	var pause := UITheme.make_round_button(UITheme.tex("icons/gi_pause.png"), "yellow", 96)
	pause.mouse_filter = Control.MOUSE_FILTER_STOP
	pause.pressed.connect(func(): pause_pressed.emit())
	box.add_child(pause)


func _counter(parent: Control, icon_path: String) -> Label:
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_END
	h.add_theme_constant_override("separation", 6)
	parent.add_child(h)
	var l := UITheme.make_label("0", 32, Color.WHITE, true, HORIZONTAL_ALIGNMENT_RIGHT)
	l.custom_minimum_size = Vector2(90, 40)
	l.pivot_offset = Vector2(60, 20)
	h.add_child(l)
	var ic := TextureRect.new()
	ic.texture = SpriteLib.tex(icon_path)
	ic.custom_minimum_size = Vector2(42, 42)
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	h.add_child(ic)
	return l


func _build_boss() -> void:
	_boss_box = VBoxContainer.new()
	_boss_box.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_boss_box.position = Vector2(-310, 214)
	_boss_box.size = Vector2(620, 90)
	_boss_box.add_theme_constant_override("separation", 2)
	_boss_box.visible = false
	_root.add_child(_boss_box)
	_boss_name = UITheme.make_label("", 30, Color(1, 0.8, 0.75), true)
	_boss_box.add_child(_boss_name)
	_boss_bar = UITheme.make_progress("red", Vector2(620, 40))
	_boss_bar.tint_progress = Color(1, 0.6, 0.6)
	_boss_box.add_child(_boss_bar)


func _on_level_coins(c: int, _total: int) -> void:
	_coins.text = str(c)
	_pulse(_coins)


func _on_gems(g: int) -> void:
	_gems.text = str(g)
	_pulse(_gems)


func _pulse(l: Control) -> void:
	l.scale = Vector2(1.3, 1.3)
	var t := l.create_tween()
	t.tween_property(l, "scale", Vector2.ONE, 0.18)


func _on_health(cur: float, mx: float) -> void:
	_hp.max_value = mx
	_hp_ghost.max_value = mx
	_hp.value = cur
	if cur < mx * 0.3:
		_hp.tint_progress = Color(1, 0.55, 0.55) if int(Time.get_ticks_msec() / 250) % 2 == 0 else Color.WHITE
	else:
		_hp.tint_progress = Color.WHITE


func _on_energy(cur: float, mx: float) -> void:
	_energy.max_value = mx
	_energy.value = cur
	var ready := cur >= Player.SPECIAL_COST
	if ready and not _special_ready.visible:
		_pulse(_energy)
	_special_ready.visible = ready


func _on_powerup(id: String, duration: float) -> void:
	if duration <= 0.0:
		return
	_on_powerup_end(id)
	var data: PowerupData = GameData.powerup(id)
	var holder := Control.new()
	holder.custom_minimum_size = Vector2(64, 64)
	_powerups.add_child(holder)
	var bar := TextureProgressBar.new()
	bar.fill_mode = TextureProgressBar.FILL_CLOCKWISE
	bar.texture_progress = SpriteLib.tex("res://assets/effects/circle_05.png")
	bar.tint_progress = Color(data.color, 0.8)
	bar.nine_patch_stretch = false
	bar.size = Vector2(64, 64)
	bar.scale = Vector2(0.5, 0.5)
	bar.value = 100
	holder.add_child(bar)
	var ic := TextureRect.new()
	ic.texture = data.icon
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ic.size = Vector2(44, 44)
	ic.position = Vector2(10, 10)
	ic.modulate = data.color
	holder.add_child(ic)
	_pu_items[id] = {"node": holder, "bar": bar, "left": duration, "total": duration}


func _on_powerup_end(id: String) -> void:
	if _pu_items.has(id):
		_pu_items[id].node.queue_free()
		_pu_items.erase(id)


func _on_boss_started(boss_name: String, _title: String) -> void:
	_boss_name.text = boss_name
	_boss_box.visible = true
	_boss_box.modulate.a = 0.0
	create_tween().tween_property(_boss_box, "modulate:a", 1.0, 0.4)


func _on_boss_hp(cur: float, mx: float) -> void:
	_boss_bar.max_value = mx
	_boss_bar.value = cur


func _hide_boss() -> void:
	create_tween().tween_property(_boss_box, "modulate:a", 0.0, 0.6)


func show_title(text: String, sub: String) -> void:
	_title.text = text
	var sl := UITheme.make_label(sub, 26, Color(1, 1, 1, 0.95), true)
	sl.position = Vector2(0, 92)
	sl.size = Vector2(680, 40)
	_title.add_child(sl)
	var t := create_tween()
	t.tween_property(_title, "modulate:a", 1.0, 0.4)
	t.tween_interval(1.8)
	t.tween_property(_title, "modulate:a", 0.0, 0.6)


func set_coins(v: int) -> void:
	_coins.text = str(v)


func set_gems(v: int) -> void:
	_gems.text = str(v)
