extends Node
## Headless smoke test: loads every script, opens every menu, builds all 24 levels and
## runs the player through each for a moment. Run:
##   godot --headless --path . res://tests/smoke_test.tscn

var failures := []


func _ready() -> void:
	await get_tree().process_frame
	_check_scripts("res://scripts")
	await _check_menus()
	await _check_levels()
	print("SMOKE RESULT: %s" % ("PASS" if failures.is_empty() else "FAIL"))
	for f in failures:
		print("  FAIL: ", f)
	get_tree().quit(0 if failures.is_empty() else 1)


func _check_scripts(dir_path: String) -> void:
	var dir := DirAccess.open(dir_path)
	for f in dir.get_files():
		if f.ends_with(".gd"):
			var s = load(dir_path + "/" + f)
			if s == null:
				failures.append("script " + f)
	for d in dir.get_directories():
		_check_scripts(dir_path + "/" + d)


func _check_menus() -> void:
	for p in ["res://scenes/menus/main_menu.tscn", "res://scenes/menus/world_select.tscn", "res://scenes/menus/level_select.tscn",
			"res://scenes/menus/character_select.tscn", "res://scenes/menus/inventory.tscn", "res://scenes/menus/shop.tscn",
			"res://scenes/menus/settings.tscn", "res://scenes/menus/credits.tscn", "res://scenes/splash/splash.tscn"]:
		var packed: PackedScene = load(p)
		if packed == null:
			failures.append("scene " + p)
			continue
		var n := packed.instantiate()
		get_tree().root.add_child(n)
		for i in 3:
			await get_tree().process_frame
		if p.ends_with("shop.tscn"):
			for t in range(6):
				n._select_tab(t)
				await get_tree().process_frame
		print("menu ok: ", p, " children=", n.get_child_count())
		n.queue_free()
		await get_tree().process_frame


func _check_levels() -> void:
	var game_packed: PackedScene = load("res://scenes/gameplay/game.tscn")
	for i in range(1, 25):
		SceneManager.params = {"level": i, "from_checkpoint": false}
		var g: Game = game_packed.instantiate()
		get_tree().root.add_child(g)
		await get_tree().physics_frame
		await get_tree().physics_frame
		var start_x := g.player.global_position.x
		Input.action_press("move_right")
		for f in 60:
			await get_tree().physics_frame
		var moved := g.player.global_position.x - start_x
		for f in 60:
			if f % 30 == 10:
				Input.action_press("jump")
			if f % 30 == 14:
				Input.action_release("jump")
			if f % 20 == 5:
				Input.action_press("attack")
			if f % 20 == 7:
				Input.action_release("attack")
			if f == 40:
				Input.action_press("special")
			if f == 42:
				Input.action_release("special")
			if f == 50:
				Input.action_press("ability")
			if f == 52:
				Input.action_release("ability")
			await get_tree().physics_frame
		Input.action_release("move_right")
		var enemies := get_tree().get_nodes_in_group("enemy").size()
		print("level %02d '%s' size=%s coins=%d enemies=%d checkpoints=%d moved=%.0f state=%s boss=%s" % [
			i, g.level.display_name, g.builder.size_px(), g.builder.total_coins, enemies, g.builder.checkpoints.size(),
			moved, g.player.machine.current_name, g.boss != null])
		if moved < 100.0:
			failures.append("level %d player did not move (%.0f)" % [i, moved])
		if g.builder.exit_gate == null:
			failures.append("level %d has no exit" % i)
		g.queue_free()
		await get_tree().process_frame
		await get_tree().process_frame
