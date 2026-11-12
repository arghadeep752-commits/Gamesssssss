extends Node
## Renders screenshots of menus and gameplay for visual QA (needs a display / Xvfb).

var out_dir := "/tmp/claude-0/-home-claude/65d9c280-3f0a-569d-b649-a04132d223d1/scratchpad/shots/"
var _current: Node


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(out_dir)
	var only := OS.get_environment("SHOTS")
	await get_tree().process_frame
	if only == "" or only == "menus":
		await _menu("res://scenes/splash/splash.tscn", "00_splash", 70)
		await _menu("res://scenes/menus/main_menu.tscn", "01_main_menu", 40)
		await _menu("res://scenes/menus/world_select.tscn", "02_world_select", 30)
		await _menu("res://scenes/menus/level_select.tscn", "03_level_select", 30, {"world": 1})
		await _menu("res://scenes/menus/character_select.tscn", "04_characters", 30)
		await _menu("res://scenes/menus/inventory.tscn", "05_inventory", 30)
		await _menu("res://scenes/menus/shop.tscn", "06_shop", 30)
		await _menu("res://scenes/menus/settings.tscn", "07_settings", 30)
	if only == "" or only == "levels":
		for spec in [[1, 0, "10_level1_start"], [1, 1400, "11_level1_run"], [3, 2900, "12_level3"], [6, 1200, "13_level6"], [10, 1500, "14_level10_ice"],
				[13, 2200, "15_level13_temple"], [17, 900, "16_level17_fire"], [21, 1400, "17_level21_shadow"], [5, 2900, "18_level5_camp"]]:
			await _level(spec[0], spec[1], spec[2])
	if only == "" or only == "bosses":
		for spec in [[4, "20_boss_samurai"], [12, "21_boss_ice"], [20, "22_boss_fire"], [24, "23_boss_king"]]:
			await _boss(spec[0], spec[1])
	get_tree().quit()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir + name + ".png")
	print("shot ", name, " ", img.get_size())


func _clear() -> void:
	if _current and is_instance_valid(_current):
		_current.queue_free()
		_current = null
	await get_tree().process_frame


func _menu(path: String, name: String, frames: int, params := {}) -> void:
	await _clear()
	SceneManager.params = params
	_current = load(path).instantiate()
	get_tree().root.add_child(_current)
	for i in frames:
		await get_tree().process_frame
	await _shot(name)


func _level(index: int, advance_x: float, name: String) -> void:
	await _clear()
	SceneManager.params = {"level": index, "from_checkpoint": false}
	var g: Game = load("res://scenes/gameplay/game.tscn").instantiate()
	_current = g
	get_tree().root.add_child(g)
	await get_tree().physics_frame
	if advance_x > 0:
		g.player.global_position.x += advance_x
		g.player.global_position.y = 200
		g.camera.snap()
	Input.action_press("move_right")
	for i in 50:
		await get_tree().physics_frame
	Input.action_press("attack")
	await get_tree().physics_frame
	Input.action_release("attack")
	for i in 6:
		await get_tree().physics_frame
	Input.action_release("move_right")
	await _shot(name)


func _boss(index: int, name: String) -> void:
	await _clear()
	SceneManager.params = {"level": index, "from_checkpoint": false}
	var g: Game = load("res://scenes/gameplay/game.tscn").instantiate()
	_current = g
	get_tree().root.add_child(g)
	await get_tree().physics_frame
	g.player.global_position = Vector2(g.builder.arena_left + 120, 17 * 64 - 4)
	g.player.max_health = 99999.0
	g.player.health = 99999.0
	g.camera.snap()
	Input.action_press("move_right")
	for i in 30:
		await get_tree().physics_frame
	Input.action_release("move_right")
	for i in 75:
		await get_tree().physics_frame
	await _shot(name + "_intro")
	for i in 100:
		await get_tree().physics_frame
	if g.boss and is_instance_valid(g.boss):
		g.player.global_position = g.boss.global_position + Vector2(-260, -10)
		g.camera.focus_on(g.boss.global_position + Vector2(-130, -230))
	for i in 20:
		await get_tree().physics_frame
	await _shot(name + "_fight")
	for i in 70:
		await get_tree().physics_frame
	await _shot(name + "_fight2")
