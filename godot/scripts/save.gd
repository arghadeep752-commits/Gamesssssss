class_name Save
extends RefCounted
## The saved game (user://save.json): money, weapons, clothes, time of day, radio.

const PATH := "user://danga_save_v1.json"


static func exists() -> bool:
	return FileAccess.file_exists(PATH)


static func fresh() -> Dictionary:
	var ammo := []
	var clip := []
	for i in Combat.DEFS.size():
		ammo.append(0)
		clip.append(0)
	return {"money": 25000, "station": 0, "hour": 9.5, "armor": 0.0, "outfit": "player_casual", "tint": [1.0, 1.0, 1.0],
		"outfits": ["player_casual"], "owned": [0, 1, 2, 3], "ammo": ammo, "clip": clip}


static func read() -> Dictionary:
	var s := fresh()
	if not exists():
		return s
	var o = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if not o is Dictionary:
		push_warning("save unreadable")
		return s
	for k in s:
		if o.has(k):
			s[k] = o[k]
	for k in ["ammo", "clip"]:
		var a: Array = s[k]
		while a.size() < Combat.DEFS.size():
			a.append(0)
	return s


static func write(s: Dictionary) -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(s))


static func delete() -> void:
	if exists():
		DirAccess.remove_absolute(PATH)
