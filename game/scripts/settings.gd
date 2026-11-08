extends Node
## Player settings (look sensitivity), saved between sessions.

const PATH := "user://chaya_settings.cfg"
const SENS_MIN := 0.3
const SENS_MAX := 2.5

var sensitivity := 1.0

func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) == OK:
		sensitivity = clampf(float(cfg.get_value("controls", "sensitivity", 1.0)), SENS_MIN, SENS_MAX)

func save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("controls", "sensitivity", sensitivity)
	cfg.save(PATH)
