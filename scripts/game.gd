extends Node3D
## Scary Aunty - the main game.
## Builds the house, the player, Scary Aunty and the HUD, and handles items,
## locks, the safe puzzle, getting caught and escaping.
##
## How to escape:
##  1. Search the nightstand in your room (top floor) -> Room Key -> open your door.
##  2. Find the Hammer in the top floor storage room.
##  3. Break the padlock on Aunty's study (middle floor) with the hammer.
##  4. Find the 4 chalk numbers (red, blue, green, yellow) and open the safe
##     in the study -> golden Main Door Key.
##  5. Take the Bolt Cutter from Aunty's bedroom (middle floor).
##  6. Front door (ground floor): key -> padlock, bolt cutter -> chain,
##     hammer -> planks. Open the door and run outside!

const HouseScript = preload("res://scripts/house.gd")
const PlayerScript = preload("res://scripts/player.gd")
const AuntyScript = preload("res://scripts/aunty.gd")
const HudScript = preload("res://scripts/hud.gd")

const ITEM_NAMES := {"room_key": "Room Key", "hammer": "Hammer", "bolt_cutter": "Bolt Cutter", "main_key": "Main Door Key"}
const MAX_LIVES := 3

var house
var player
var aunty
var hud
var inventory: Array = ["", "", "", "", "", ""]
var selected := -1
var lives := MAX_LIVES
var code: Array = []
var focus = null
var state := "intro"   # intro, play, caught, won, lost
var play_time := 0.0
var safe_open := false
var front_door_open := false
var aunty_chasing := false

var music_bgm: AudioStreamPlayer
var music_chase: AudioStreamPlayer
var _chase_mix := 0.0
var _floor_t := 0.0
var _settle_t := 1.5


func _ready() -> void:
	randomize()
	code = [randi() % 10, randi() % 10, randi() % 10, randi() % 10]
	_make_environment()

	house = HouseScript.new()
	house.name = "House"
	house.game = self
	add_child(house)
	house.build(code)

	player = PlayerScript.new()
	player.name = "Player"
	player.game = self
	add_child(player)
	player.global_position = house.spawn_player
	player.set_look(house.spawn_player_yaw, 0.0)

	aunty = AuntyScript.new()
	aunty.name = "ScaryAunty"
	add_child(aunty)
	aunty.setup(self, house)
	aunty.global_position = house.spawn_aunty

	hud = HudScript.new()
	hud.name = "HUD"
	add_child(hud)
	hud.setup(self)

	_make_music()
	_intro()
	print("SCARY_AUNTY_READY doors=%d waypoints=%d sketchfab_models=%d chalk_font=%s" % [
		house.doors.size(), house.astar.get_point_count(), Assets.models.size(), str(Assets.has_chalk_font)])


## Godot's default sun + sky with filmic tone mapping and a light colour grade.
func _make_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.385, 0.454, 0.55)
	sky_mat.sky_horizon_color = Color(0.6463, 0.6558, 0.6708)
	sky_mat.ground_bottom_color = Color(0.2, 0.169, 0.133)
	sky_mat.ground_horizon_color = Color(0.6463, 0.6558, 0.6708)
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.adjustment_enabled = true
	env.adjustment_brightness = 1.0
	env.adjustment_contrast = 1.06
	env.adjustment_saturation = 1.1
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-55.0, 150.0, 0.0)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 40.0
	sun.light_energy = 1.0
	add_child(sun)


func _make_music() -> void:
	music_bgm = AudioStreamPlayer.new()
	music_bgm.stream = Assets.get_music("music_bgm")
	music_bgm.volume_db = -17.0
	add_child(music_bgm)
	if music_bgm.stream != null:
		music_bgm.play()
	music_chase = AudioStreamPlayer.new()
	music_chase.stream = Assets.get_music("music_chase")
	music_chase.volume_db = -60.0
	add_child(music_chase)
	if music_chase.stream != null:
		music_chase.play()


func _wait(t: float) -> void:
	var tm := Timer.new()
	tm.one_shot = true
	tm.wait_time = t
	add_child(tm)
	tm.start()
	await tm.timeout
	tm.queue_free()


func _intro() -> void:
	state = "intro"
	hud.fade_from_black(1.8)
	hud.show_subtitle("Ugh... my head... Where am I?", 2.6)
	await _wait(2.9)
	hud.show_subtitle("This is Scary Aunty's house! She kidnapped me!", 3.0)
	await _wait(3.2)
	hud.show_subtitle("I have to escape before she finds me!", 3.0)
	await _wait(3.2)
	if state == "intro":
		state = "play"
	hud.show_subtitle("Tip: tap the bulb if you need a hint.", 3.0, Color(1.0, 0.95, 0.6))
	aunty.activate(3.0)


# ================================================================ every frame

func _process(delta: float) -> void:
	if state == "play":
		play_time += delta
	_update_focus()
	_update_music(delta)
	_settle_t -= delta
	_floor_t -= delta
	if _floor_t <= 0.0 and _settle_t <= 0.0:
		_floor_t = 0.2
		var p: Vector3 = player.global_position
		if p.x < 0.6:
			house.set_visible_floors(1, true)  # at the front door / outside: show the whole house
		else:
			house.set_visible_floors(player_floor(), p.x > 8.0 and p.z < 6.6)
	if state == "play" and front_door_open and player.global_position.x < -0.7:
		_win()


func player_floor() -> int:
	return clampi(int(floor((player.global_position.y + 1.0) / 3.0)), 0, 2)


func _update_focus() -> void:
	var f = null
	if (state == "play" or state == "intro") and player.controls_enabled:
		f = player.get_focus()
	focus = f
	if f != null:
		hud.set_hand(true, _prompt_for(f))
	else:
		hud.set_hand(false, "")


func _prompt_for(it) -> String:
	if it.kind == "door":
		if it.target == house.front_door and not house.front_locks.is_empty():
			return "Locked"
		return it.target.get_prompt()
	if it.kind == "search" and it.data.get("done", false):
		return "Empty"
	return str(it.prompt)


func _update_music(delta: float) -> void:
	var want := 1.0 if aunty_chasing and state == "play" else 0.0
	_chase_mix = move_toward(_chase_mix, want, delta * (1.5 if want > 0.5 else 0.4))
	if music_bgm != null:
		music_bgm.volume_db = lerpf(-17.0, -40.0, _chase_mix)
	if music_chase != null:
		music_chase.volume_db = lerpf(-60.0, -9.0, sqrt(_chase_mix))


# ================================================================ using things

func interact() -> void:
	if (state != "play" and state != "intro") or focus == null or not is_instance_valid(focus):
		return
	var it = focus
	match str(it.kind):
		"pickup":
			_pickup(it)
		"door":
			_use_door(it.target)
		"lock":
			_use_lock(it)
		"safe":
			_use_safe()
		"note":
			hud.open_note(str(it.data.get("text", "")))
		"search":
			_search(it)


func _pickup(it) -> void:
	var slot := inventory.find("")
	if slot == -1:
		hud.show_subtitle("My pockets are full!", 2.0)
		return
	inventory[slot] = str(it.item_id)
	selected = slot
	Assets.play_2d("pickup", -2.0)
	hud.show_subtitle("Got the %s!" % ITEM_NAMES.get(str(it.item_id), "item"), 2.2)
	focus = null
	it.queue_free()
	hud.refresh_inventory()


func _use_door(door) -> void:
	if door == house.front_door:
		_use_front_door()
		return
	if door.locked:
		if door == house.start_door and has_item("room_key"):
			remove_item("room_key")
			door.locked = false
			house.enable_room_points(door)
			Assets.play_3d("unlock", door.global_position + Vector3(0, 1.0, 0), house, 0.0)
			hud.show_subtitle("The key worked! I'm out of my room.", 2.6)
			door.set_open(true)
			return
		door.rattle()
		hud.show_subtitle(str(door.lock_message), 2.8)
		make_noise(door.global_position, 5.0)
		return
	door.toggle()


func _use_front_door() -> void:
	var door = house.front_door
	if not house.front_locks.is_empty():
		door.rattle()
		var need := PackedStringArray()
		if house.front_locks.has("front_padlock"):
			need.append("a padlock")
		if house.front_locks.has("front_chain"):
			need.append("a chain")
		if house.front_locks.has("front_planks"):
			need.append("wooden planks")
		hud.show_subtitle("The front door is blocked by " + ", ".join(need) + "!", 3.0)
		make_noise(door.global_position, 6.0)
		return
	door.locked = false
	if not door.is_open:
		door.set_open(true)
		front_door_open = true
		hud.show_subtitle("The door is open! RUN OUTSIDE!", 2.6)


func _use_lock(it) -> void:
	var needs := str(it.data.get("needs", ""))
	var lock_id := str(it.data.get("lock", ""))
	if not has_item(needs):
		var msg := "I need something to open this."
		if needs == "hammer":
			msg = "I need something heavy to break this..."
		elif needs == "bolt_cutter":
			msg = "This chain is too strong. I need a cutter!"
		elif needs == "main_key":
			msg = "A big padlock. I need the main door key."
		hud.show_subtitle(msg, 2.6)
		Assets.play_3d("locked", it.global_position, house, -4.0)
		return
	if needs == "main_key":
		remove_item("main_key")
	var snd := "break_metal"
	var radius := 14.0
	if lock_id == "front_planks":
		snd = "break_wood"
	elif lock_id == "front_chain":
		snd = "cut"
	elif lock_id == "front_padlock":
		snd = "unlock"
		radius = 6.0
	Assets.play_3d(snd, it.global_position, house, 3.0)
	make_noise(it.global_position, radius)
	focus = null
	_drop_away(it)
	if lock_id == "study_padlock":
		house.study_door.locked = false
		house.enable_room_points(house.study_door)
		hud.show_subtitle("I broke the padlock! I hope Aunty didn't hear that...", 3.0)
		return
	house.front_locks.erase(lock_id)
	if house.front_locks.is_empty():
		hud.show_subtitle("That was the last lock! Open the front door!", 3.0)
	else:
		hud.show_subtitle("One lock gone! %d more to go." % house.front_locks.size(), 2.6)


func _drop_away(node) -> void:
	node.collision_layer = 0
	var tw := create_tween()
	tw.tween_property(node, "position:y", node.position.y - 0.9, 0.45).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.parallel().tween_property(node, "rotation:z", 1.3, 0.45)
	tw.tween_property(node, "scale", Vector3(0.01, 0.01, 0.01), 0.25)
	tw.tween_callback(node.queue_free)


func _use_safe() -> void:
	if safe_open:
		hud.show_subtitle("The safe is empty now.", 2.0)
		return
	hud.open_keypad()


## Called by the keypad. Returns true if the code is right.
func try_code(entered: Array) -> bool:
	var ok := entered.size() == 4
	if ok:
		for i in range(4):
			if int(entered[i]) != int(code[i]):
				ok = false
	if ok:
		safe_open = true
		Assets.play_2d("right", 0.0)
		house.open_safe()
		hud.show_subtitle("Click! The safe is open. There's a golden key inside!", 3.2)
	else:
		Assets.play_2d("wrong", 0.0)
	return ok


func _search(it) -> void:
	if it.data.get("done", false):
		hud.show_subtitle("Nothing else here.", 1.8)
		return
	it.data["done"] = true
	Assets.play_3d("drawer", it.global_position + Vector3(0, 0.4, 0), house, 0.0)
	var sp: Vector3 = it.data.get("spawn", it.global_position)
	house.spawn_item(int(it.data.get("floor", 0)), str(it.data.get("item_id", "room_key")), sp, 0.3)
	hud.show_subtitle("There's a small key in the drawer!", 2.6)


func has_item(id: String) -> bool:
	return id != "" and inventory.has(id)


func remove_item(id: String) -> void:
	var i := inventory.find(id)
	if i != -1:
		inventory[i] = ""
		if selected == i:
			selected = -1
	hud.refresh_inventory()


func select_slot(i: int) -> void:
	if i < 0 or i >= inventory.size():
		return
	if str(inventory[i]) == "" or selected == i:
		selected = -1
	else:
		selected = i
		Assets.play_2d("click", -8.0)
		hud.show_subtitle(str(ITEM_NAMES.get(str(inventory[i]), "")), 1.4)
	hud.refresh_inventory()


func get_hint() -> String:
	if house.start_door.locked:
		return "Search the furniture in this room. Aunty keeps a spare key somewhere here."
	if not has_item("hammer") and (house.study_door.locked or house.front_locks.has("front_planks")):
		return "Look for a hammer in the storage room on the top floor."
	if house.study_door.locked:
		return "Aunty's study on the middle floor has a padlock. Break it with the hammer!"
	if not safe_open:
		return "Find the 4 chalk numbers on the walls (red, blue, green, yellow) and open the safe in the study. Aunty's note tells the order."
	if house.front_locks.has("front_padlock") and not has_item("main_key"):
		return "Take the golden key from the safe in the study."
	if house.front_locks.has("front_chain") and not has_item("bolt_cutter"):
		return "Aunty's bedroom on the middle floor has a bolt cutter for the chain."
	if not house.front_locks.is_empty():
		return "Go to the front door on the ground floor and remove the locks."
	return "The front door is free. Open it and run outside!"


# ================================================================ noise + aunty events

func make_noise(pos: Vector3, radius: float) -> void:
	if aunty != null:
		aunty.hear(pos, radius)


func on_player_step() -> void:
	make_noise(player.global_position, 3.5)


func player_can_be_seen() -> bool:
	return state == "play"


func on_aunty_chase_start() -> void:
	aunty_chasing = true
	Assets.play_2d("sting", -3.0)


func on_aunty_chase_end() -> void:
	aunty_chasing = false


func aunty_says(text: String) -> void:
	if player.global_position.distance_to(aunty.global_position) < 20.0:
		hud.show_subtitle("Aunty: " + text, 2.4, Color(1.0, 0.45, 0.4))


func on_caught() -> void:
	if state != "play":
		return
	state = "caught"
	aunty_chasing = false
	player.controls_enabled = false
	player.move_input = Vector2.ZERO
	hud.release_touches()
	hud.set_hand(false, "")
	Assets.play_2d("caught", 2.0)
	Input.vibrate_handheld(500)
	var to: Vector3 = aunty.global_position - player.global_position
	var want_yaw := atan2(-to.x, -to.z)
	var y0: float = player.yaw
	var p0: float = player.pitch
	var tw := create_tween()
	tw.tween_method(func(v: float): player.set_look(lerp_angle(y0, want_yaw, v), lerpf(p0, 0.1, v)), 0.0, 1.0, 0.35)
	var lines := ["Gotcha!", "Back to your room, naughty boy!", "Caught you!"]
	hud.show_subtitle("Aunty: " + str(lines[randi() % lines.size()]), 2.0, Color(1.0, 0.45, 0.4))
	hud.flash_red()
	await _wait(1.3)
	hud.fade_to_black(0.6)
	await _wait(0.8)
	lives -= 1
	if lives <= 0:
		state = "lost"
		Assets.play_2d("lose", 0.0)
		hud.show_game_over()
		return
	player.global_position = house.spawn_player
	player.velocity = Vector3.ZERO
	player.set_look(house.spawn_player_yaw, 0.0)
	aunty.respawn(house.spawn_aunty)
	await _wait(0.5)
	hud.fade_from_black(1.0)
	hud.show_subtitle("She threw me back in my room... Chances left: %d" % lives, 3.2)
	player.controls_enabled = true
	state = "play"
	aunty.activate(5.0)


func _win() -> void:
	state = "won"
	player.controls_enabled = false
	player.move_input = Vector2.ZERO
	aunty.freeze()
	aunty_chasing = false
	Assets.play_2d("win", 0.0)
	hud.show_win(play_time)


# ================================================================ pause / menus

func pause_game() -> void:
	if state == "won" or state == "lost" or get_tree().paused:
		return
	get_tree().paused = true
	hud.open_pause()


func restart() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()


func to_menu() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
