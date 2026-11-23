extends CanvasLayer
## On-screen controls, laid out like Evil Nun's:
##   top left      - pause button (opens the pause menu with the sensitivity setting)
##   left          - crouch button (shows a standing or crouching figure)
##   bottom left   - joystick to walk
##   right         - hand + USE, only while you look at something you can use (the door);
##                   that thing also gets a small marker with its name
##   anywhere else - drag to look around
## Every finger is tracked on its own, so you can walk, look and press a button at the same time.

const STAND_ICON := preload("res://assets/ui/stand.png")
const CROUCH_ICON := preload("res://assets/ui/crouch.png")
const BUTTON_MARGIN := 18.0      # buttons are a bit easier to hit than they look
const JOYSTICK_GRAB := 1.4       # a touch this far from the joystick (in radii) still grabs it
const JOYSTICK_TRAVEL := 0.42    # how far the knob can move, as a part of the ring's radius
const DEAD_ZONE := 0.12

var player: Node                 # set by main.gd

var _joy_finger := -1
var _look_finger := -1
var _message_tween: Tween

@onready var crouch_button: TextureRect = %CrouchButton
@onready var pause_button: TextureRect = %PauseButton
@onready var joystick: TextureRect = %Joystick
@onready var knob: TextureRect = %Knob
@onready var hand_button: TextureRect = %HandButton
@onready var object_marker: Control = %ObjectMarker
@onready var object_name: Label = %ObjectName
@onready var message: Label = %Message
@onready var settings_panel: Control = %SettingsPanel
@onready var slider: HSlider = %SensitivitySlider
@onready var value_label: Label = %SensitivityValue
@onready var click_sound: AudioStreamPlayer = %ClickSound
@onready var fade: ColorRect = %Fade


func _ready() -> void:
	settings_panel.hide()
	hand_button.hide()
	object_marker.hide()
	message.modulate.a = 0.0

	slider.min_value = Settings.MIN_SENSITIVITY
	slider.max_value = Settings.MAX_SENSITIVITY
	slider.step = 0.1
	slider.value = Settings.sensitivity
	_show_sensitivity()
	slider.value_changed.connect(_on_sensitivity_changed)
	%Minus.pressed.connect(_on_minus_pressed)
	%Plus.pressed.connect(_on_plus_pressed)
	%Resume.pressed.connect(close_settings)

	# the room fades in from black
	fade.show()
	fade.modulate.a = 1.0
	create_tween().tween_property(fade, "modulate:a", 0.0, 1.8).set_delay(0.3)


func _process(_delta: float) -> void:
	if player == null:
		return
	var target: Node = null if settings_panel.visible else player.get_interactable()
	hand_button.visible = target != null
	object_marker.visible = target != null and _place_marker(target)
	crouch_button.texture = CROUCH_ICON if player.crouching else STAND_ICON


## Puts the marker and the name (e.g. DOOR) on top of the thing you can use.
func _place_marker(target: Node) -> bool:
	var camera: Camera3D = player.camera
	var spot: Vector3 = target.get_marker_position()
	if camera.is_position_behind(spot):
		return false
	object_marker.position = camera.unproject_position(spot)
	object_name.text = target.display_name
	return true


func _input(event: InputEvent) -> void:
	if settings_panel.visible:
		# the settings panel uses normal buttons; only Esc / Back closes it from here
		if event.is_action_pressed("pause"):
			close_settings()
			get_viewport().set_input_as_handled()
		return

	if event is InputEventScreenTouch:
		_on_touch(event)
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		_on_drag(event)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("crouch"):
		player.toggle_crouch()
	elif event.is_action_pressed("interact"):
		player.interact()
	elif event.is_action_pressed("pause"):
		open_settings()


func _notification(what: int) -> void:
	# Android back button opens / closes the settings instead of quitting
	if what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if settings_panel.visible:
			close_settings()
		else:
			open_settings()


func show_message(text: String) -> void:
	message.text = text
	if _message_tween:
		_message_tween.kill()
	_message_tween = create_tween()
	_message_tween.tween_property(message, "modulate:a", 1.0, 0.15)
	_message_tween.tween_interval(1.6)
	_message_tween.tween_property(message, "modulate:a", 0.0, 0.6)


func open_settings() -> void:
	_click()
	_let_go_of_everything()
	settings_panel.show()
	get_tree().paused = true


func close_settings() -> void:
	_click()
	Settings.save()
	settings_panel.hide()
	get_tree().paused = false


func _on_touch(event: InputEventScreenTouch) -> void:
	var pos := event.position
	if event.pressed:
		if _is_over(crouch_button, pos):
			player.toggle_crouch()
		elif _is_over(pause_button, pos):
			open_settings()
		elif hand_button.visible and _is_over(hand_button, pos):
			player.interact()
		elif _joy_finger == -1 and pos.distance_to(_joystick_center()) < _joystick_radius() * JOYSTICK_GRAB:
			_joy_finger = event.index
			_move_knob(pos)
		elif _look_finger == -1:
			_look_finger = event.index
	else:
		if event.index == _joy_finger:
			_joy_finger = -1
			_move_knob(_joystick_center())
		if event.index == _look_finger:
			_look_finger = -1


func _on_drag(event: InputEventScreenDrag) -> void:
	if event.index == _joy_finger:
		_move_knob(event.position)
	elif event.index == _look_finger:
		player.look(event.relative)


func _move_knob(pos: Vector2) -> void:
	var travel := _joystick_radius() * JOYSTICK_TRAVEL
	var offset := (pos - _joystick_center()).limit_length(travel)
	knob.position = (joystick.size - knob.size) * 0.5 + offset
	var amount := offset / travel
	player.move_input = amount if amount.length() > DEAD_ZONE else Vector2.ZERO


func _let_go_of_everything() -> void:
	_joy_finger = -1
	_look_finger = -1
	_move_knob(_joystick_center())


func _joystick_center() -> Vector2:
	return joystick.get_global_rect().get_center()


func _joystick_radius() -> float:
	return joystick.size.x * 0.5


func _is_over(control: Control, pos: Vector2) -> bool:
	return control.get_global_rect().grow(BUTTON_MARGIN).has_point(pos)


func _on_sensitivity_changed(value: float) -> void:
	Settings.sensitivity = value
	_show_sensitivity()


func _on_minus_pressed() -> void:
	_click()
	slider.value -= slider.step


func _on_plus_pressed() -> void:
	_click()
	slider.value += slider.step


func _show_sensitivity() -> void:
	value_label.text = "%.1f" % slider.value


func _click() -> void:
	click_sound.play()
