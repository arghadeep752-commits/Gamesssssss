extends Node
## Persistent progression + settings. JSON in user://, validated against defaults,
## written atomically with a backup copy so a crash mid-write can't wipe progress.

const SAVE_PATH := "user://ninja_save.json"
const BACKUP_PATH := "user://ninja_save.bak"
const TEMP_PATH := "user://ninja_save.tmp"
const VERSION := 1

var data: Dictionary = {}
var _dirty := false
var _save_timer := 0.0


static func default_settings() -> Dictionary:
	return {
		"music": 0.75,
		"sfx": 0.9,
		"vibration": true,
		"quality": 1,               # 0 low, 1 medium, 2 high
		"sensitivity": 1.0,         # joystick sensitivity
		"controls_scale": 1.0,
		"controls_opacity": 0.8,
		"language": "en",
		"show_fps": false,
		"layout": {},               # control_id -> [x_ratio, y_ratio]
	}


static func default_data() -> Dictionary:
	return {
		"version": VERSION,
		"coins": 0,
		"gems": 0,
		"unlocked_level": 1,
		"last_level": 1,
		"completed_levels": {},
		"unlocked_characters": ["main_ninja"],
		"selected_character": "main_ninja",
		"owned_weapons": ["katana"],
		"equipped_weapon": "katana",
		"weapon_levels": {"katana": 1},
		"owned_skins": ["original"],
		"equipped_skins": {},
		"health_upgrades": 0,
		"consumables": {},
		"double_jump_unlocked": false,
		"defeated_bosses": [],
		"checkpoints": {},
		"settings": default_settings(),
		"stats": {"enemies": 0, "deaths": 0, "playtime": 0.0, "coins_total": 0},
	}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	load_game()


func _process(delta: float) -> void:
	if _dirty:
		_save_timer -= delta
		if _save_timer <= 0.0:
			save_game()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if _dirty:
			save_game()


# ------------------------------------------------------------------ io
func load_game() -> void:
	var loaded := _read_json(SAVE_PATH)
	if loaded.is_empty():
		loaded = _read_json(BACKUP_PATH)
	data = _validate(loaded)


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("Save file corrupted: %s" % path)
		return {}
	return parsed


func save_game() -> void:
	_dirty = false
	var text := JSON.stringify(data, "\t")
	var f := FileAccess.open(TEMP_PATH, FileAccess.WRITE)
	if f == null:
		push_warning("Could not write save")
		return
	f.store_string(text)
	f.close()
	var dir := DirAccess.open("user://")
	if dir == null:
		return
	if FileAccess.file_exists(SAVE_PATH):
		dir.copy(SAVE_PATH, BACKUP_PATH)
	dir.rename(TEMP_PATH, SAVE_PATH)


func mark_dirty(immediate := false) -> void:
	_dirty = true
	_save_timer = 0.0 if immediate else 0.6
	if immediate:
		save_game()


func _validate(src: Dictionary) -> Dictionary:
	var out := default_data()
	for key in out.keys():
		if src.has(key) and typeof(src[key]) == typeof(out[key]):
			out[key] = src[key]
		elif src.has(key) and typeof(out[key]) == TYPE_FLOAT and typeof(src[key]) == TYPE_INT:
			out[key] = float(src[key])
		elif src.has(key) and typeof(out[key]) == TYPE_INT and typeof(src[key]) == TYPE_FLOAT:
			out[key] = int(src[key])
	# nested settings with defaults
	var s := default_settings()
	if typeof(out.settings) == TYPE_DICTIONARY:
		for k in s.keys():
			if out.settings.has(k) and (typeof(out.settings[k]) == typeof(s[k]) or (typeof(s[k]) == TYPE_FLOAT and typeof(out.settings[k]) == TYPE_INT)):
				s[k] = out.settings[k]
	out.settings = s
	out.coins = max(0, int(out.coins))
	out.gems = max(0, int(out.gems))
	out.unlocked_level = clampi(int(out.unlocked_level), 1, 24)
	out.last_level = clampi(int(out.last_level), 1, 24)
	if not out.unlocked_characters.has("main_ninja"):
		out.unlocked_characters.append("main_ninja")
	if not out.owned_weapons.has("katana"):
		out.owned_weapons.append("katana")
	if not out.owned_skins.has("original"):
		out.owned_skins.append("original")
	if not out.unlocked_characters.has(out.selected_character):
		out.selected_character = "main_ninja"
	if not out.owned_weapons.has(out.equipped_weapon):
		out.equipped_weapon = "katana"
	for w in out.owned_weapons:
		if not out.weapon_levels.has(w):
			out.weapon_levels[w] = 1
	out.version = VERSION
	return out


func reset_progress() -> void:
	var keep_settings: Dictionary = data.get("settings", default_settings())
	data = default_data()
	data.settings = keep_settings
	mark_dirty(true)
	Events.currency_changed.emit()


# ------------------------------------------------------------- currency
func coins() -> int:
	return int(data.coins)


func gems() -> int:
	return int(data.gems)


func add_coins(amount: int) -> void:
	data.coins = max(0, int(data.coins) + amount)
	if amount > 0:
		data.stats.coins_total = int(data.stats.get("coins_total", 0)) + amount
	mark_dirty()
	Events.currency_changed.emit()


func add_gems(amount: int) -> void:
	data.gems = max(0, int(data.gems) + amount)
	mark_dirty()
	Events.currency_changed.emit()


func can_afford(coins_cost: int, gems_cost: int) -> bool:
	return coins() >= coins_cost and gems() >= gems_cost


func spend(coins_cost: int, gems_cost: int) -> bool:
	if not can_afford(coins_cost, gems_cost):
		return false
	data.coins = coins() - coins_cost
	data.gems = gems() - gems_cost
	mark_dirty(true)
	Events.currency_changed.emit()
	return true


# ------------------------------------------------------------ progression
func is_level_unlocked(index: int) -> bool:
	return index <= int(data.unlocked_level)


func is_level_completed(index: int) -> bool:
	return data.completed_levels.has(str(index))


func level_stars(index: int) -> int:
	return int(data.completed_levels.get(str(index), {}).get("stars", 0))


func world_stars(world_id: int) -> int:
	var total := 0
	for i in range(1, 5):
		total += level_stars((world_id - 1) * 4 + i)
	return total


func is_world_unlocked(world_id: int) -> bool:
	return is_level_unlocked((world_id - 1) * 4 + 1)


func complete_level(index: int, stars: int, time: float, coins_collected: int) -> Dictionary:
	var key := str(index)
	var prev: Dictionary = data.completed_levels.get(key, {})
	var first_time := prev.is_empty()
	var rec := {
		"stars": max(stars, int(prev.get("stars", 0))),
		"best_time": min(time, float(prev.get("best_time", 99999.0))),
		"coins": max(coins_collected, int(prev.get("coins", 0))),
	}
	data.completed_levels[key] = rec
	if index < 24:
		data.unlocked_level = max(int(data.unlocked_level), index + 1)
	data.last_level = min(index + 1, 24)
	data.checkpoints.erase(key)
	_apply_level_unlocks(index)
	mark_dirty(true)
	return {"first_time": first_time}


func _apply_level_unlocks(index: int) -> void:
	for c in GameData.characters:
		if c.unlock_type == "level" and index >= c.unlock_level and not data.unlocked_characters.has(c.id):
			data.unlocked_characters.append(c.id)
			Events.toast.emit("NEW NINJA UNLOCKED: %s" % c.display_name, Color(1, 0.85, 0.3))
	for w in GameData.weapons:
		if w.unlock_type == "level" and index >= w.unlock_level and not data.owned_weapons.has(w.id):
			data.owned_weapons.append(w.id)
			data.weapon_levels[w.id] = 1
			Events.toast.emit("NEW WEAPON: %s" % w.display_name, Color(0.6, 0.9, 1))


func boss_defeated(boss_id: String) -> void:
	if not data.defeated_bosses.has(boss_id):
		data.defeated_bosses.append(boss_id)
	if boss_id == "shadow_samurai":
		data.double_jump_unlocked = true
	mark_dirty(true)


func set_checkpoint(index: int, checkpoint_id: int, pos: Vector2) -> void:
	data.checkpoints[str(index)] = {"id": checkpoint_id, "x": pos.x, "y": pos.y}
	mark_dirty()


func get_checkpoint(index: int) -> Dictionary:
	return data.checkpoints.get(str(index), {})


func clear_checkpoint(index: int) -> void:
	data.checkpoints.erase(str(index))
	mark_dirty()


# ------------------------------------------------------- owned content
func is_character_unlocked(id: String) -> bool:
	return data.unlocked_characters.has(id)


func unlock_character(id: String) -> void:
	if not data.unlocked_characters.has(id):
		data.unlocked_characters.append(id)
	mark_dirty(true)


func select_character(id: String) -> void:
	if is_character_unlocked(id):
		data.selected_character = id
		mark_dirty(true)


func selected_character() -> CharacterData:
	return GameData.character(data.selected_character)


func owns_weapon(id: String) -> bool:
	return data.owned_weapons.has(id)


func add_weapon(id: String) -> void:
	if not data.owned_weapons.has(id):
		data.owned_weapons.append(id)
		data.weapon_levels[id] = 1
	mark_dirty(true)


func weapon_level(id: String) -> int:
	return int(data.weapon_levels.get(id, 1))


func upgrade_weapon(id: String) -> void:
	data.weapon_levels[id] = weapon_level(id) + 1
	mark_dirty(true)


func equip_weapon(id: String) -> void:
	if owns_weapon(id):
		data.equipped_weapon = id
		mark_dirty(true)


func equipped_weapon() -> WeaponData:
	return GameData.weapon(data.equipped_weapon)


func owns_skin(id: String) -> bool:
	return data.owned_skins.has(id)


func add_skin(id: String) -> void:
	if not data.owned_skins.has(id):
		data.owned_skins.append(id)
	mark_dirty(true)


func equipped_skin(character_id: String) -> String:
	return str(data.equipped_skins.get(character_id, ""))


func equip_skin(character_id: String, skin_id: String) -> void:
	data.equipped_skins[character_id] = skin_id
	mark_dirty(true)


func consumable_count(id: String) -> int:
	return int(data.consumables.get(id, 0))


func add_consumable(id: String, amount := 1) -> void:
	data.consumables[id] = max(0, consumable_count(id) + amount)
	mark_dirty(true)


func health_bonus() -> float:
	return 20.0 * float(data.health_upgrades)


# ------------------------------------------------------------- settings
func setting(key: String):
	return data.settings.get(key, default_settings().get(key))


func set_setting(key: String, value) -> void:
	data.settings[key] = value
	mark_dirty()
	Events.settings_changed.emit()


func add_stat(key: String, amount: float) -> void:
	data.stats[key] = float(data.stats.get(key, 0)) + amount
	_dirty = true
