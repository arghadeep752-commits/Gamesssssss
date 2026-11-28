extends Node
## Global settings for Scary Aunty (saved on the phone).

const SETTINGS_PATH := "user://settings.cfg"
const MIN_SENS := 0.2
const MAX_SENS := 3.0

var sensitivity: float = 1.0


func _ready() -> void:
	load_settings()


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) == OK:
		sensitivity = float(cfg.get_value("controls", "sensitivity", 1.0))
	sensitivity = clampf(sensitivity, MIN_SENS, MAX_SENS)


func set_sensitivity(value: float) -> void:
	sensitivity = clampf(snappedf(value, 0.1), MIN_SENS, MAX_SENS)
	save_settings()


func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("controls", "sensitivity", sensitivity)
	cfg.save(SETTINGS_PATH)
