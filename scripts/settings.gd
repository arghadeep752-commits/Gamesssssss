extends Node
## Autoload "Settings": keeps the player's settings and saves them on the phone.
## For now there is only one setting - how fast the camera turns (look sensitivity).

const SAVE_PATH := "user://settings.cfg"
const MIN_SENSITIVITY := 0.2
const MAX_SENSITIVITY := 3.0
const DEFAULT_SENSITIVITY := 1.0

var sensitivity := DEFAULT_SENSITIVITY


func _ready() -> void:
	var file := ConfigFile.new()
	if file.load(SAVE_PATH) == OK:
		sensitivity = file.get_value("controls", "sensitivity", DEFAULT_SENSITIVITY)
	sensitivity = clampf(sensitivity, MIN_SENSITIVITY, MAX_SENSITIVITY)


func save() -> void:
	var file := ConfigFile.new()
	file.set_value("controls", "sensitivity", sensitivity)
	file.save(SAVE_PATH)
