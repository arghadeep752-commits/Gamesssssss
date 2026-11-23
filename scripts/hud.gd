extends CanvasLayer
## On-screen controls:
##   bottom left   - joystick to walk
##   right         - USE button, only while the pointer is on something you can use (the door)
##   middle        - a small pointer circle; the name of what you aim at shows under it
##   anywhere else - drag to look around
## Every finger is tracked on its own, so you can walk, look and press USE at the same time.

const BUTTON_MARGIN := 18.0      # the USE button is a bit easier to hit than it looks
const JOYSTICK_GRAB := 1.4       # a touch this far from the joystick (in radii) still grabs it
const JOYSTICK_TRAVEL := 0.42    # how far the knob can move, as a part of the ring's radius
const DEAD_ZONE := 0.12

var player: Node                 # set by main.gd

var _joy_finger := -1
var _look_finger := -1
var _message_tween: Tween

@onready var joystick: TextureRect = %Joystick
@onready var knob: TextureRect = %Knob
@onready var use_button: TextureRect = %UseButton
@onready var object_name: Label = %ObjectName
@onready var message: Label = %Message
@onready var fade: ColorRect = %Fade


func _ready() -> void:
	use_button.hide()
	object_name.hide()
	message.modulate.a = 0.0
	# the room fades in from black
	fade.show()
	fade.modulate.a = 1.0
	create_tween().tween_property(fade, "modulate:a", 0.0, 1.8).set_delay(0.3)


func _process(_delta: float) -> void:
	if player == null:
		return
	var target: Node = player.get_interactable()
	use_button.visible = target != null
	object_name.visible = target != null
	if target:
		object_name.text = target.display_name


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		_on_touch(event)
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		_on_drag(event)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("interact"):
		player.interact()


func show_message(text: String) -> void:
	message.text = text
	if _message_tween:
		_message_tween.kill()
	_message_tween = create_tween()
	_message_tween.tween_property(message, "modulate:a", 1.0, 0.15)
	_message_tween.tween_interval(1.6)
	_message_tween.tween_property(message, "modulate:a", 0.0, 0.6)


func _on_touch(event: InputEventScreenTouch) -> void:
	var pos := event.position
	if event.pressed:
		if use_button.visible and use_button.get_global_rect().grow(BUTTON_MARGIN).has_point(pos):
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


func _joystick_center() -> Vector2:
	return joystick.get_global_rect().get_center()


func _joystick_radius() -> float:
	return joystick.size.x * 0.5
