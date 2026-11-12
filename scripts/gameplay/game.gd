class_name Game
extends Node2D
## Gameplay scene: builds the level, spawns the ninja, enemies and boss, and runs
## checkpoints, lives, completion, game over, boss intro/defeat and pause.

const START_LIVES := 3

var level_index := 1
var level: LevelData
var world: Dictionary
var builder: LevelBuilder
var player: Player
var camera: CameraRig
var hud: HUD
var controls: TouchControls
var pause_menu: PauseMenu
var overlays: GameOverlays
var boss: Boss
var level_root: Node2D
var level_coins := 0
var level_gems := 0
var lives := START_LIVES
var deaths := 0
var time := 0.0
var finished := false
var boss_triggered := false
var respawn_pos := Vector2.ZERO
var _arena_wall: StaticBody2D
var _hit_stop_left := 0.0
var _player_light: Sprite2D


func _ready() -> void:
	add_to_group("game")
	process_mode = Node.PROCESS_MODE_PAUSABLE
	level_index = int(SceneManager.params.get("level", SaveManager.data.last_level))
	level = GameData.level(level_index)
	world = GameData.world(level.world)
	Pool.clear()
	_build_world()
	_build_ui()
	_spawn_player()
	_spawn_enemies()
	_setup_boss_arena()
	_apply_start_boosts()
	Events.hit_stop.connect(_on_hit_stop)
	Events.toast.connect(func(_t, _c): pass)
	AudioManager.play_music(world.music, 1.2)
	hud.show_title(level.display_name.to_upper(), "WORLD %d-%d  •  %s" % [level.world, (level_index - 1) % 4 + 1, level.objective.to_upper()])
	Events.level_coins_changed.emit(0, builder.total_coins)
	Events.player_lives_changed.emit(lives)
	hud.set_gems(SaveManager.gems())


func _build_world() -> void:
	level_root = Node2D.new()
	level_root.name = "Level"
	add_child(level_root)
	builder = LevelBuilder.new()
	builder.build(level, level_root)
	camera = CameraRig.new()
	add_child(camera)
	camera.setup_limits(builder.size_px())
	var bg := WorldBackground.new()
	bg.name = "Background"
	add_child(bg)
	move_child(bg, 0)
	bg.build(world, builder.size_px(), camera, level_index)
	for cp in builder.checkpoints:
		cp.activated.connect(_on_checkpoint)
	if builder.exit_gate:
		builder.exit_gate.reached.connect(_on_exit_reached)
	for b in builder.breakables:
		b.broken.connect(_on_breakable_broken)
	# light sources (torches, lava glow) in the darker worlds
	if world.light:
		for l in builder.lights:
			var s := Effects.light(level_root, l[0], l[1], l[2])
			s.z_index = 3


func _build_ui() -> void:
	hud = HUD.new()
	add_child(hud)
	hud.pause_pressed.connect(toggle_pause)
	controls = TouchControls.new()
	add_child(controls)
	pause_menu = PauseMenu.new()
	add_child(pause_menu)
	pause_menu.resume_requested.connect(toggle_pause)
	pause_menu.restart_requested.connect(func():
		get_tree().paused = false
		SaveManager.clear_checkpoint(level_index)
		SceneManager.start_level(level_index, false))
	pause_menu.quit_requested.connect(func():
		get_tree().paused = false
		SceneManager.goto_menu("res://scenes/menus/level_select.tscn", {"world": level.world}))
	overlays = GameOverlays.new()
	add_child(overlays)


func _spawn_player() -> void:
	player = Player.new()
	player.name = "Player"
	level_root.add_child(player)
	var c := SaveManager.selected_character()
	var w := SaveManager.equipped_weapon()
	player.setup(c, w, SaveManager.weapon_level(w.id), SaveManager.health_bonus(), bool(SaveManager.data.double_jump_unlocked))
	player.level_bottom = LevelBuilder.PIT_Y
	player.ice = level.world == 3
	player.died.connect(_on_player_died)
	respawn_pos = builder.player_start
	var cp := SaveManager.get_checkpoint(level_index)
	if SceneManager.params.get("from_checkpoint", true) and not cp.is_empty():
		var idx := int(cp.id)
		if idx >= 0 and idx < builder.checkpoints.size():
			var node: Checkpoint = builder.checkpoints[idx]
			node.activate(false)
			for i in idx:
				builder.checkpoints[i].activate(false)
			respawn_pos = node.global_position + Vector2(0, 40)
	player.global_position = respawn_pos
	player.safe_pos = respawn_pos
	camera.target = player
	camera.snap()
	if world.light:
		_player_light = Effects.light(player, Vector2(0, -50), Color(1, 0.85, 0.6, 0.22), 3.2)
		_player_light.z_index = -1
	for pk in builder.entities.get_children():
		if pk is Pickup:
			pk.magnet_target = player


func _spawn_enemies() -> void:
	for e in builder.pending_enemies:
		spawn_enemy(e.id, e.pos)


func spawn_enemy(id: String, pos: Vector2) -> Enemy:
	var e := Enemy.create(id, level.difficulty)
	e.position = pos
	level_root.add_child(e)
	return e


func _apply_start_boosts() -> void:
	var used := []
	for id in ["shield", "speed_boost", "critical_strike", "double_jump", "energy_boost"]:
		if SaveManager.consumable_count(id) > 0:
			SaveManager.add_consumable(id, -1)
			used.append(id)
	if used.is_empty():
		return
	await get_tree().create_timer(1.2).timeout
	for id in used:
		player.apply_powerup(id)


func _process(delta: float) -> void:
	if not finished and not get_tree().paused:
		time += delta
		SaveManager.add_stat("playtime", delta)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") and not finished:
		toggle_pause()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if not finished and not get_tree().paused and is_inside_tree():
			toggle_pause()
	elif what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if not finished:
			toggle_pause()


func toggle_pause() -> void:
	if finished:
		return
	var p := not get_tree().paused
	get_tree().paused = p
	controls.release_all()
	if p:
		pause_menu.open()
		AudioManager.duck_music(-12.0, 0.2)
	else:
		pause_menu.close()
		AudioManager.unduck_music(0.3)


# ------------------------------------------------------------ callbacks
func on_coin_collected(value: int) -> void:
	level_coins += value
	SaveManager.add_coins(value)
	Events.level_coins_changed.emit(level_coins, builder.total_coins)


func on_gem_collected(value: int) -> void:
	level_gems += value
	SaveManager.add_gems(value)
	Events.gems_changed.emit(SaveManager.gems())


func spawn_coins(pos: Vector2, count: int) -> void:
	for i in count:
		var pk := Pickup.create("coin", SpriteLib.tex("res://assets/environments/props/coin_gold.png"), 1)
		level_root.add_child.call_deferred(pk)
		pk.position = pos
		pk.magnet_target = player
		var target := pos + Vector2(randf_range(-70, 70), randf_range(-60, 10))
		pk.flying = true
		var t := pk.create_tween()
		t.tween_property(pk, "position", target, 0.35).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.tween_callback(func():
			pk._base_y = pk.position.y
			pk.flying = false)


func _on_breakable_broken(b: Breakable, at: Vector2) -> void:
	match b.kind:
		"coin_block":
			var pk := Pickup.create("coin", SpriteLib.tex("res://assets/environments/props/coin_gold.png"), 1)
			level_root.add_child(pk)
			pk.position = at
			pk._base_y = at.y
			pk.flying = true
			pk.monitoring = false
			on_coin_collected(1)
			AudioManager.play_sfx("coin", 0.05)
			var t := pk.create_tween()
			t.tween_property(pk, "position:y", at.y - 70, 0.25)
			t.parallel().tween_property(pk, "modulate:a", 0.0, 0.3)
			t.tween_callback(pk.queue_free)
		"crate":
			var r := randf()
			if r < 0.25:
				_drop_pickup("heart", at)
			elif r < 0.33:
				_drop_pickup("gem", at)
			else:
				spawn_coins(at, randi_range(2, 4))
		"chest":
			spawn_coins(at + Vector2(0, -30), b.coins_inside)
			_drop_pickup("gem", at + Vector2(0, -40))
			if randf() < 0.5:
				var ids := ["shield", "speed_boost", "critical_strike", "energy_boost"]
				_drop_powerup(ids[randi() % ids.size()], at + Vector2(40, -40))
			Effects.burst(level_root, at, "star_04", Color(1, 0.9, 0.4), 16, 420.0, 0.6, 0.12)
		"secret":
			AudioManager.play_sfx("secret", 0.0)
			Events.toast.emit("SECRET FOUND!", Color(0.6, 1.0, 0.7))


func _drop_pickup(kind: String, at: Vector2) -> void:
	var tex: String = "heart" if kind == "heart" else ["gem_blue", "gem_green", "gem_red", "gem_yellow"][randi() % 4]
	var pk := Pickup.create(kind, SpriteLib.tex("res://assets/environments/props/%s.png" % tex), 1)
	level_root.add_child.call_deferred(pk)
	pk.position = at
	pk.magnet_target = player


func _drop_powerup(id: String, at: Vector2) -> void:
	var d: PowerupData = GameData.powerup(id)
	var pk := Pickup.create("powerup", d.icon, 1, id)
	pk.sprite.modulate = d.color
	level_root.add_child.call_deferred(pk)
	pk.position = at


func _on_checkpoint(cp: Checkpoint) -> void:
	respawn_pos = cp.global_position + Vector2(0, 40)
	SaveManager.set_checkpoint(level_index, cp.index, respawn_pos)
	Events.toast.emit("CHECKPOINT", Color(0.55, 1.0, 0.6))
	player.heal(15.0)


func _on_hit_stop(duration: float) -> void:
	if int(SaveManager.setting("quality")) == 0 or finished:
		return
	Engine.time_scale = 0.08
	_hit_stop_left = duration
	await get_tree().create_timer(duration, true, false, true).timeout
	if Engine.time_scale < 0.5 and (boss == null or not boss.dead):
		Engine.time_scale = 1.0


func _on_player_died() -> void:
	deaths += 1
	lives -= 1
	SaveManager.add_stat("deaths", 1)
	Events.player_lives_changed.emit(max(lives, 0))
	if lives > 0:
		overlays.show_banner("%d %s LEFT" % [lives, "LIFE" if lives == 1 else "LIVES"], Color(1, 0.6, 0.5), 1.0)
		await get_tree().create_timer(0.8).timeout
		player.respawn_at(respawn_pos)
		camera.snap()
		if boss and not boss.dead and boss_triggered:
			# keep the fight going; nudge the player away from the boss
			player.global_position = Vector2(builder.arena_left + 140.0, 17 * 64.0 - 2.0)
			player.safe_pos = player.global_position
		return
	finished = true
	controls.set_enabled(false)
	AudioManager.stop_music(0.5)
	overlays.show_game_over(
		func(): SceneManager.start_level(level_index, true),
		func(): SceneManager.goto_menu("res://scenes/menus/level_select.tscn", {"world": level.world}))


# ----------------------------------------------------------------- boss
func _setup_boss_arena() -> void:
	if level.boss_id == "" or builder.boss_spawn == Vector2.ZERO:
		return
	boss = Boss.create(level.boss_id)
	boss.position = builder.boss_spawn
	boss.arena = Vector2(builder.arena_left, builder.arena_right)
	boss.facing = -1.0
	level_root.add_child(boss)
	boss.defeated.connect(_on_boss_defeated)
	var trigger := Area2D.new()
	trigger.collision_layer = 0
	trigger.collision_mask = 2
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(80, 1400)
	cs.shape = r
	trigger.add_child(cs)
	trigger.position = Vector2(builder.arena_left + 260.0, 700)
	level_root.add_child(trigger)
	trigger.body_entered.connect(func(b):
		if b == player and not boss_triggered:
			boss_triggered = true
			trigger.queue_free.call_deferred()
			_start_boss_intro())


func _start_boss_intro() -> void:
	# lock the arena behind the player
	_arena_wall = StaticBody2D.new()
	_arena_wall.collision_layer = 1
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(64, 1600)
	cs.shape = r
	_arena_wall.add_child(cs)
	_arena_wall.position = Vector2(builder.arena_left - 32.0, 200)
	level_root.add_child.call_deferred(_arena_wall)
	var gate_sprite := Sprite2D.new()
	gate_sprite.texture = SpriteLib.tex("res://assets/environments/props/block_strong_danger.png")
	for i in 3:
		var g: Sprite2D = gate_sprite.duplicate()
		g.position = Vector2(builder.arena_left - 32.0, (14 + i) * 64 + 32)
		level_root.add_child.call_deferred(g)
	camera.set_arena_limits(builder.arena_left - 64.0, builder.arena_right)
	player.controls_enabled = false
	controls.set_enabled(false)
	player.velocity.x = 0
	AudioManager.stop_music(0.6)
	camera.focus_on(boss.global_position + Vector2(-120, -260))
	var data: Dictionary = GameData.BOSSES[level.boss_id]
	overlays.show_boss_intro(data.name, data.title, 2.6)
	AudioManager.play_sfx("ready", 0.0)
	Events.camera_shake.emit(5.0, 0.4)
	await get_tree().create_timer(2.7).timeout
	camera.focus_on(null)
	player.controls_enabled = true
	controls.set_enabled(true)
	AudioManager.play_music("final_boss" if level.boss_id == "shadow_king" else ("boss" if level.world % 2 == 1 else "boss2"), 0.5)
	Events.boss_started.emit(data.name, data.title)
	boss.start_fight()


func _on_boss_defeated(b: Boss) -> void:
	var data: Dictionary = GameData.BOSSES[b.boss_id]
	Events.boss_defeated.emit(b.boss_id)
	SaveManager.boss_defeated(b.boss_id)
	AudioManager.play_sfx("boss_defeat", 0.0)
	AudioManager.play_sfx("boss_win", 0.0)
	overlays.show_banner("%s DEFEATED!" % data.name, Color(1, 0.85, 0.3), 2.2)
	spawn_coins(b.global_position + Vector2(0, -80), 20)
	SaveManager.add_coins(int(data.reward_coins))
	SaveManager.add_gems(int(data.reward_gems))
	Events.gems_changed.emit(SaveManager.gems())
	Events.toast.emit("+%d COINS   +%d GEMS" % [data.reward_coins, data.reward_gems], Color(1, 0.9, 0.4))
	camera.setup_limits(builder.size_px())
	if builder.exit_gate:
		builder.exit_gate.unlock()
	AudioManager.play_music(world.music, 2.0)
	if b.boss_id == "shadow_samurai" and not player.permanent_double_jump:
		player.permanent_double_jump = true
		await get_tree().create_timer(2.4).timeout
		overlays.show_banner("NEW ABILITY:\nDOUBLE JUMP!", Color(0.6, 0.9, 1.0), 2.0)


# ------------------------------------------------------------ complete
func _on_exit_reached() -> void:
	if finished:
		return
	finished = true
	controls.set_enabled(false)
	player.celebrate()
	var ratio: float = float(level_coins) / maxf(1.0, float(builder.total_coins))
	var stars := 1 + (1 if ratio >= 0.7 else 0) + (1 if deaths == 0 else 0)
	var reward := 50 + level_index * 10 + (stars - 1) * 25
	SaveManager.add_coins(reward)
	var res := SaveManager.complete_level(level_index, stars, time, level_coins)
	AudioManager.stop_music(0.4)
	await get_tree().create_timer(1.2).timeout
	if level_index == GameData.LEVEL_COUNT:
		overlays.show_victory(
			func(): SceneManager.goto_menu("res://scenes/menus/credits.tscn"),
			func(): SceneManager.goto_menu("res://scenes/menus/main_menu.tscn"))
		return
	overlays.show_level_complete(level.display_name, stars, level_coins, level_gems, time, reward, true,
		func(): SceneManager.start_level(level_index + 1, true),
		func(): SceneManager.start_level(level_index, false),
		func(): SceneManager.goto_menu("res://scenes/menus/level_select.tscn", {"world": GameData.level(min(level_index + 1, 24)).world}))


func _exit_tree() -> void:
	Engine.time_scale = 1.0
	if controls:
		controls.release_all()
