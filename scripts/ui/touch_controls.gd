class_name TouchControls
extends CanvasLayer
## Multitouch mobile controls: floating joystick (left) + Jump / Attack / Special / Ability
## buttons (right). Feeds the regular InputMap actions, so keyboard and touch share one path.
## Supports per-control repositioning (edit_mode) saved in settings.

const DEFAULT_LAYOUT := {
	"joystick": Vector2(0.20, 0.84),
	"jump": Vector2(0.86, 0.87),
	"attack": Vector2(0.65, 0.90),
	"special": Vector2(0.88, 0.70),
	"ability": Vector2(0.67, 0.74),
}
const SIZES := {"joystick": 250.0, "jump": 150.0, "attack": 150.0, "special": 112.0, "ability": 112.0}
const ACTIONS := {"jump": "jump", "attack": "attack", "special": "special", "ability": "ability"}

var edit_mode := false
var controls := {}          # id -> Control (centered via pivot)
var _touch_owner := {}      # touch index -> control id
var _joy_touch := -1
var _joy_center := Vector2.ZERO
var _joy_base: TextureRect
var _joy_nub: TextureRect
var _root: Control
var _special_ring: TextureProgressBar
var _ability_cd: TextureProgressBar
var _drag_offset := Vector2.ZERO
var _scale := 1.0
var _enabled := true


func _ready() -> void:
	layer = 11
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_build()
	apply_settings()
	get_viewport().size_changed.connect(apply_settings)
	Events.settings_changed.connect(apply_settings)
	Events.player_energy_changed.connect(func(c, m): _special_ring.value = c / m * 100.0)
	Events.ability_cooldown_changed.connect(func(r): _ability_cd.value = r * 100.0)


func _build() -> void:
	# joystick
	var joy := Control.new()
	joy.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(joy)
	_joy_base = _tex_rect("controls/a_joystick_circle_pad_a.png", Vector2(250, 250))
	joy.add_child(_joy_base)
	_joy_nub = _tex_rect("controls/a_joystick_circle_nub_a.png", Vector2(120, 120))
	joy.add_child(_joy_nub)
	controls["joystick"] = joy
	_add_button("jump", "icon_jump", Color(0.55, 0.85, 1.0))
	_add_button("attack", "icon_sword", Color(1.0, 0.6, 0.5))
	_add_button("special", "icon_burst", Color(0.8, 0.6, 1.0))
	var w := SaveManager.equipped_weapon()
	var ab_icon: String = {"dash_slash": "icon_arrow", "whirlwind": "icon_arrow_rotate", "fan_throw": "icon_star", "power_shot": "icon_target", "flame_wave": "icon_fire"}.get(w.ability_id, "icon_star")
	_add_button("ability", ab_icon, Color(1.0, 0.85, 0.45))
	_special_ring = _ring(controls["special"], Color(0.75, 0.55, 1.0, 0.9), false)
	_ability_cd = _ring(controls["ability"], Color(0, 0, 0, 0.55), true)
	_ability_cd.value = 0


func _tex_rect(rel: String, size: Vector2) -> TextureRect:
	var t := TextureRect.new()
	t.texture = UITheme.tex(rel)
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.size = size
	t.position = -size / 2.0
	t.pivot_offset = size / 2.0
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


func _add_button(id: String, icon_name: String, tint: Color) -> void:
	var c := Control.new()
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(c)
	var s: float = SIZES[id]
	var bg := _tex_rect("controls/a_button_circle.png", Vector2(s, s))
	bg.name = "Bg"
	bg.modulate = Color(1, 1, 1, 1)
	c.add_child(bg)
	var ic := _tex_rect("icons/%s.png" % icon_name, Vector2(s * 0.55, s * 0.55))
	ic.name = "Icon"
	ic.modulate = tint
	c.add_child(ic)
	controls[id] = c


func _ring(parent: Control, color: Color, overlay: bool) -> TextureProgressBar:
	var s := 112.0
	var r := TextureProgressBar.new()
	r.fill_mode = TextureProgressBar.FILL_CLOCKWISE
	r.texture_progress = SpriteLib.tex("res://assets/effects/circle_05.png" if not overlay else "res://assets/ui/controls/a_button_circle.png")
	r.nine_patch_stretch = true
	r.size = Vector2(s, s) * (1.25 if not overlay else 1.0)
	r.position = -r.size / 2.0
	r.tint_progress = color
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.value = 0
	if not overlay:
		r.show_behind_parent = true
		parent.add_child(r)
		parent.move_child(r, 0)
	else:
		parent.add_child(r)
	return r


func apply_settings() -> void:
	var vp := get_viewport().get_visible_rect().size
	_scale = float(SaveManager.setting("controls_scale"))
	var opacity := float(SaveManager.setting("controls_opacity"))
	var layout: Dictionary = SaveManager.setting("layout")
	for id in controls:
		var n: Vector2 = DEFAULT_LAYOUT[id]
		if layout.has(id) and layout[id] is Array and layout[id].size() == 2:
			n = Vector2(float(layout[id][0]), float(layout[id][1]))
		var c: Control = controls[id]
		c.position = Vector2(n.x * vp.x, n.y * vp.y)
		c.scale = Vector2(_scale, _scale)
		c.modulate.a = opacity
	_joy_center = controls["joystick"].position
	_joy_nub.position = -_joy_nub.size / 2.0


func set_enabled(on: bool) -> void:
	_enabled = on
	if not on:
		release_all()
	_root.visible = on


func release_all() -> void:
	for a in ["move_left", "move_right", "move_up", "move_down", "jump", "attack", "special", "ability"]:
		Input.action_release(a)
	_touch_owner.clear()
	_joy_touch = -1
	if controls.has("joystick"):
		_joy_nub.position = -_joy_nub.size / 2.0
		controls["joystick"].position = _joy_center
	for id in ACTIONS:
		_press_visual(id, false)


func _radius(id: String) -> float:
	return SIZES[id] * 0.5 * _scale * 1.2


func _hit(pos: Vector2) -> String:
	var best := ""
	var best_d := INF
	for id in ACTIONS:
		var c: Control = controls[id]
		var d := pos.distance_to(c.position)
		if d < _radius(id) and d < best_d:
			best = id
			best_d = d
	return best


func _input(event: InputEvent) -> void:
	if not _enabled or not _root.visible:
		return
	if event is InputEventScreenTouch:
		_on_touch(event)
	elif event is InputEventScreenDrag:
		_on_drag(event)


func _on_touch(e: InputEventScreenTouch) -> void:
	var vp := get_viewport().get_visible_rect().size
	var pos := e.position
	if e.pressed:
		if edit_mode:
			var id := _hit(pos)
			if id == "" and pos.distance_to(controls["joystick"].position) < 140.0 * _scale:
				id = "joystick"
			if id != "":
				_touch_owner[e.index] = id
				_drag_offset = controls[id].position - pos
				get_viewport().set_input_as_handled()
			return
		var id := _hit(pos)
		if id != "":
			_touch_owner[e.index] = id
			Input.action_press(ACTIONS[id])
			_press_visual(id, true)
			Haptics.light()
			get_viewport().set_input_as_handled()
			return
		if _joy_touch == -1 and pos.x < vp.x * 0.5 and pos.y > vp.y * 0.45:
			_joy_touch = e.index
			controls["joystick"].position = pos
			_joy_nub.position = -_joy_nub.size / 2.0
			get_viewport().set_input_as_handled()
	else:
		if edit_mode and _touch_owner.has(e.index):
			_save_layout()
			_touch_owner.erase(e.index)
			return
		if _touch_owner.has(e.index):
			var id: String = _touch_owner[e.index]
			_touch_owner.erase(e.index)
			if not _touch_owner.values().has(id):
				Input.action_release(ACTIONS[id])
				_press_visual(id, false)
		if e.index == _joy_touch:
			_joy_touch = -1
			_set_axis(Vector2.ZERO)
			var t := create_tween()
			t.tween_property(controls["joystick"], "position", _joy_center, 0.12)
			t.parallel().tween_property(_joy_nub, "position", -_joy_nub.size / 2.0, 0.12)


func _on_drag(e: InputEventScreenDrag) -> void:
	if edit_mode:
		if _touch_owner.has(e.index):
			var id: String = _touch_owner[e.index]
			controls[id].position = e.position + _drag_offset
			if id == "joystick":
				_joy_center = controls[id].position
		return
	if e.index != _joy_touch:
		return
	var center: Vector2 = controls["joystick"].position
	var max_r := 95.0 * _scale
	var d := e.position - center
	if d.length() > max_r * 1.6:
		# let the base follow the thumb for a comfortable floating stick
		controls["joystick"].position = e.position - d.normalized() * max_r * 1.6
		center = controls["joystick"].position
		d = e.position - center
	var clamped := d.limit_length(max_r)
	_joy_nub.position = clamped / _scale - _joy_nub.size / 2.0
	_set_axis(clamped / max_r)
	get_viewport().set_input_as_handled()


func _set_axis(v: Vector2) -> void:
	var sens := float(SaveManager.setting("sensitivity"))
	var x := v.x * (0.75 + sens * 0.5)
	var dead := 0.18
	Input.action_release("move_left")
	Input.action_release("move_right")
	if x > dead:
		Input.action_press("move_right", clampf((x - dead) / (1.0 - dead) * 1.15, 0.0, 1.0))
	elif x < -dead:
		Input.action_press("move_left", clampf((-x - dead) / (1.0 - dead) * 1.15, 0.0, 1.0))
	if v.y < -0.55:
		Input.action_press("move_up")
	else:
		Input.action_release("move_up")
	if v.y > 0.55:
		Input.action_press("move_down")
	else:
		Input.action_release("move_down")


func _press_visual(id: String, down: bool) -> void:
	var c: Control = controls[id]
	var bg: TextureRect = c.get_node("Bg")
	var t := c.create_tween()
	t.tween_property(bg, "scale", Vector2(0.88, 0.88) if down else Vector2.ONE, 0.06)
	bg.modulate = Color(0.75, 0.75, 0.8) if down else Color.WHITE


func _save_layout() -> void:
	var vp := get_viewport().get_visible_rect().size
	var layout := {}
	for id in controls:
		var p: Vector2 = controls[id].position
		layout[id] = [clampf(p.x / vp.x, 0.05, 0.95), clampf(p.y / vp.y, 0.3, 0.97)]
	SaveManager.set_setting("layout", layout)


func reset_layout() -> void:
	SaveManager.set_setting("layout", {})
	apply_settings()
