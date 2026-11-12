extends Node
## Headless gameplay-flow test: bosses (intro, damage, phase 2, defeat, exit unlock, level
## completion), enemies, pickups, checkpoints, death / respawn / game over, shop + save.

var failures := []
var log_lines := []


func _ready() -> void:
	await get_tree().process_frame
	SaveManager.reset_progress()
	await _test_bosses()
	await _test_level_systems()
	_test_economy_and_save()
	print("FLOW RESULT: %s" % ("PASS" if failures.is_empty() else "FAIL"))
	for l in log_lines:
		print("  ", l)
	for f in failures:
		print("  FAIL: ", f)
	SaveManager.reset_progress()
	get_tree().quit(0 if failures.is_empty() else 1)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _new_game(index: int) -> Game:
	SceneManager.params = {"level": index, "from_checkpoint": false}
	var g: Game = load("res://scenes/gameplay/game.tscn").instantiate()
	get_tree().root.add_child(g)
	await _frames(2)
	return g


func _test_bosses() -> void:
	for index in [4, 8, 12, 16, 20, 24]:
		var g := await _new_game(index)
		var p := g.player
		p.max_health = 999999.0
		p.health = 999999.0
		p.global_position = Vector2(g.builder.arena_left + 300, 17 * 64 - 2)
		await _frames(3)
		if not g.boss_triggered:
			failures.append("boss %d: arena trigger did not fire" % index)
			g._start_boss_intro()
		await _frames(190)
		var b := g.boss
		if b == null or not b.active:
			failures.append("boss %d not active after intro" % index)
			g.queue_free()
			await _frames(2)
			continue
		var start_hp := b.hp
		var moved := false
		var b_start := b.global_position
		# let the boss run its patterns for a while
		var patterns_seen := {}
		for t in 300:
			await get_tree().physics_frame
			if b.global_position.distance_to(b_start) > 50:
				moved = true
			if b._last_patterns.size() > 0:
				patterns_seen[b._last_patterns[-1]] = true
		# attack it
		var hits := 0
		for t in 240:
			if not is_instance_valid(b) or b.dead:
				break
			p.global_position = b.global_position + Vector2(-110 if b.facing > 0 else 110, 0)
			p.facing = signf(b.global_position.x - p.global_position.x)
			if t % 12 == 0:
				Input.action_press("attack")
			if t % 12 == 2:
				Input.action_release("attack")
			await get_tree().physics_frame
		var dealt := start_hp - (b.hp if is_instance_valid(b) else 0.0)
		if dealt <= 0:
			failures.append("boss %d took no damage" % index)
		# finish it
		if is_instance_valid(b) and not b.dead:
			b.take_damage(b.hp * 0.6, b.global_position, 0, false)
			await _frames(5)
			var phase := b.phase
			b.take_damage(b.hp + 10.0, b.global_position, 0, false)
			if phase != 2:
				failures.append("boss %d never entered phase 2" % index)
		await _frames(150)
		if is_instance_valid(b):
			await _frames(60)
		var unlocked := g.builder.exit_gate and not g.builder.exit_gate.locked
		if not unlocked:
			failures.append("boss %d: exit not unlocked after defeat" % index)
		Engine.time_scale = 1.0
		# walk into the exit
		p.global_position = g.builder.exit_gate.global_position + Vector2(-20, 30)
		await _frames(40)
		if not g.finished:
			failures.append("boss level %d not completed at exit" % index)
		log_lines.append("boss L%02d %-15s moved=%s dealt=%.0f patterns=%s completed=%s" % [index, b.boss_id if is_instance_valid(b) else "(defeated)", moved, dealt, patterns_seen.keys(), g.finished])
		if not moved:
			failures.append("boss %d never moved" % index)
		g.queue_free()
		await _frames(3)
	if not bool(SaveManager.data.double_jump_unlocked):
		failures.append("double jump not unlocked after shadow samurai")


func _test_level_systems() -> void:
	var g := await _new_game(2)
	var p := g.player
	# coins
	var coin: Pickup = null
	for n in g.builder.entities.get_children():
		if n is Pickup and n.kind == "coin":
			coin = n
			break
	var before := g.level_coins
	p.global_position = coin.global_position + Vector2(0, 40)
	await _frames(6)
	if g.level_coins <= before:
		failures.append("coin pickup not collected")
	# enemy kill
	var enemy: Enemy = null
	for n in get_tree().get_nodes_in_group("enemy"):
		if n is Enemy:
			enemy = n
			break
	if enemy:
		for t in 120:
			if not is_instance_valid(enemy) or enemy.dead:
				break
			p.global_position = enemy.global_position + Vector2(-70, 0)
			p.facing = 1.0
			if t % 10 == 0:
				Input.action_press("attack")
			if t % 10 == 2:
				Input.action_release("attack")
			await get_tree().physics_frame
		if is_instance_valid(enemy) and not enemy.dead:
			failures.append("could not kill enemy %s" % enemy.id)
		else:
			log_lines.append("enemy killed ok")
	# crate / chest
	var chest: Breakable = null
	for n in g.builder.breakables:
		if is_instance_valid(n) and n.kind == "chest":
			chest = n
	if chest:
		p.global_position = chest.global_position + Vector2(0, 20)
		await _frames(10)
		if is_instance_valid(chest) and not chest._opened:
			failures.append("chest did not open on touch")
		else:
			log_lines.append("chest opened ok")
	# checkpoint
	var cp: Checkpoint = g.builder.checkpoints[0]
	p.global_position = cp.global_position + Vector2(0, 30)
	await _frames(6)
	if not cp.active or SaveManager.get_checkpoint(2).is_empty():
		failures.append("checkpoint not activated/saved")
	else:
		log_lines.append("checkpoint saved ok")
	# pit death + respawn
	await _frames(10)
	var hp := p.health
	p.global_position = Vector2(p.global_position.x, g.builder.size_px().y + 400)
	await _frames(40)
	if p.health >= hp:
		failures.append("pit fall did no damage")
	if p.global_position.y > g.builder.size_px().y:
		failures.append("player not returned from pit")
	# death -> lives
	p.invuln = 0
	p.take_damage(99999, p.global_position, 100, false)
	await _frames(150)
	if g.lives != 2:
		failures.append("lives not decremented (%d)" % g.lives)
	if p.is_dead():
		failures.append("player not respawned after death")
	# game over
	for i in 2:
		p.invuln = 0
		p.take_damage(99999, p.global_position, 100, false)
		await _frames(150)
	if not g.finished:
		failures.append("game over not triggered")
	else:
		log_lines.append("game over ok")
	g.queue_free()
	await _frames(3)
	# exit of a normal level
	g = await _new_game(1)
	g.player.global_position = g.builder.exit_gate.global_position + Vector2(-10, 30)
	await _frames(100)
	if not g.finished or not SaveManager.is_level_completed(1):
		failures.append("level 1 completion not recorded")
	else:
		log_lines.append("level complete ok, stars=%d" % SaveManager.level_stars(1))
	g.queue_free()
	await _frames(3)


func _test_economy_and_save() -> void:
	SaveManager.add_coins(5000)
	var c0 := SaveManager.coins()
	if not SaveManager.spend(1200, 0):
		failures.append("spend failed")
	SaveManager.add_weapon("dual_blades")
	SaveManager.upgrade_weapon("katana")
	SaveManager.equip_weapon("dual_blades")
	SaveManager.save_game()
	var copy := SaveManager.data.duplicate(true)
	SaveManager.load_game()
	if SaveManager.coins() != c0 - 1200 or not SaveManager.owns_weapon("dual_blades") or SaveManager.weapon_level("katana") != 2:
		failures.append("save/load mismatch")
	if SaveManager.spend(999999, 0):
		failures.append("overspend allowed")
	# corrupted file falls back safely
	var f := FileAccess.open(SaveManager.SAVE_PATH, FileAccess.WRITE)
	f.store_string("{not json")
	f.close()
	SaveManager.load_game()
	if SaveManager.data.is_empty() or not SaveManager.data.has("coins"):
		failures.append("corrupted save not handled")
	log_lines.append("economy/save ok, coins after reload=%d" % SaveManager.coins())
