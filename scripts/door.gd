extends StaticBody3D
## The locked door. You can try the handle as often as you like - it never opens.

signal tried_locked

## Name shown on screen when you look at the door.
@export var display_name := "DOOR"
## Real recordings of a door handle being rattled; one is picked at random.
@export var rattle_sounds: Array[AudioStream] = []

var _busy := false

@onready var panel: Node3D = $Panel
@onready var knob: Node3D = $Panel/Knob
@onready var rattle_player: AudioStreamPlayer3D = $RattleSound
@onready var _rest := panel.position


## Where the on-screen marker goes: the middle of the door, a bit above the knob.
func get_marker_position() -> Vector3:
	return to_global(Vector3(0, 1.3, 0.05))


func interact() -> void:
	tried_locked.emit()
	if _busy:
		return
	_busy = true
	if not rattle_sounds.is_empty():
		rattle_player.stream = rattle_sounds.pick_random()
		rattle_player.play()

	# turn the knob, shake the door against the lock a few times, let go
	var tween := create_tween()
	tween.tween_property(knob, "rotation:z", deg_to_rad(-35.0), 0.12)
	for i in 4:
		tween.tween_property(panel, "position:z", _rest.z - 0.006, 0.05)
		tween.tween_property(panel, "position:z", _rest.z + 0.002, 0.06)
	tween.tween_property(panel, "position", _rest, 0.05)
	tween.tween_property(knob, "rotation:z", 0.0, 0.18)
	tween.finished.connect(func() -> void: _busy = false)
