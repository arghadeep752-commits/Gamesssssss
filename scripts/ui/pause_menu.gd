class_name PauseMenu
extends CanvasLayer
## Pause menu with quick audio settings.

signal resume_requested
signal restart_requested
signal quit_requested

var _root: Control


func _ready() -> void:
	layer = 25
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = UITheme.theme
	add_child(_root)
	var dim := ColorRect.new()
	dim.color = Color(0.03, 0.02, 0.06, 0.72)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var panel := UITheme.make_panel("brown")
	panel.custom_minimum_size = Vector2(580, 0)
	center.add_child(panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 16)
	panel.add_child(v)
	v.add_child(UITheme.make_title("PAUSED", 60))
	var resume := UITheme.make_button("RESUME", "green", Vector2(460, 104))
	resume.pressed.connect(func(): resume_requested.emit())
	v.add_child(resume)
	var restart := UITheme.make_button("RESTART", "yellow", Vector2(460, 104))
	restart.pressed.connect(func(): restart_requested.emit())
	v.add_child(restart)
	v.add_child(_slider_row("Music", "music"))
	v.add_child(_slider_row("Sound", "sfx"))
	var vib := CheckBox.new()
	vib.text = "  Vibration"
	vib.button_pressed = bool(SaveManager.setting("vibration"))
	vib.toggled.connect(func(on): SaveManager.set_setting("vibration", on))
	v.add_child(vib)
	var quit := UITheme.make_button("QUIT TO MAP", "red", Vector2(460, 104))
	quit.pressed.connect(func(): quit_requested.emit())
	v.add_child(quit)


func _slider_row(label: String, key: String) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	var l := UITheme.make_label(label, 28, Color.WHITE, true, HORIZONTAL_ALIGNMENT_LEFT)
	l.custom_minimum_size = Vector2(130, 0)
	h.add_child(l)
	var s := UITheme.make_slider(float(SaveManager.setting(key)))
	s.custom_minimum_size = Vector2(340, 48)
	s.value_changed.connect(func(val): SaveManager.set_setting(key, val))
	h.add_child(s)
	return h


func open() -> void:
	visible = true
	_root.modulate.a = 0.0
	create_tween().tween_property(_root, "modulate:a", 1.0, 0.15)


func close() -> void:
	visible = false
