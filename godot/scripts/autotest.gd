extends Node
## Only in the test build (feature "dgtest") or with --dg-test: plays through the game - menu, settings, the house,
## walking, the phone and a cheat, shooting, the bike, a car, the palace, the map, the gun shop, the boat, the
## helicopter, night and the police - and prints "[DG-TEST] SNAP name" so the cloud test takes a screenshot.

var out_dir := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	if OS.get_name() != "Android":
		out_dir = "/tmp/dgtest/"
		DirAccess.make_dir_recursive_absolute(out_dir)
	run()


func log_t(s: String) -> void:
	print("[DG-TEST] " + s)


func wait(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func snap(name: String) -> void:
	for i in 3:
		await get_tree().process_frame
	log_t("SNAP %s fps=%d chunks=%d cars=%d peds=%d" % [name, Engine.get_frames_per_second(), G.city.loaded_chunks,
		G.traffic.cars.size(), G.traffic.peds.size()])
	if out_dir != "" and DisplayServer.get_name() != "headless":
		get_viewport().get_texture().get_image().save_png(out_dir + name + ".png")
	await wait(2.0 if out_dir != "" else 4.0)     # on Android the cloud test grabs the screen meanwhile


func run() -> void:
	var g: Game = G.game
	await wait(3.0)
	log_t("start %s gpu=%s" % [str(get_viewport().get_visible_rect().size), RenderingServer.get_video_adapter_name()])
	await snap("01-menu")
	G.menus.settings(G.menus.main_menu)
	await wait(1.0)
	await snap("02-settings")
	G.menus.main_menu()
	await wait(0.5)
	g.play(false)
	await wait(4.0)
	var p := Player.I
	Hud.scripted = true
	Wanted.never = true
	await snap("03-home")
	Hud.s_move = Vector2(0, 1)
	await wait(2.5)
	Hud.s_move = Vector2.ZERO
	await snap("04-walk")
	G.menus.phone()
	await wait(1.0)
	await snap("05-phone")
	G.menus.close()
	g.cheat("4545")
	g.cheat("1122")
	p.equip(Combat.PISTOL)
	await wait(0.5)
	Hud.s_fire = true
	await wait(1.2)
	await snap("06-shoot")
	Hud.s_fire = false
	p.equip(Combat.FIST)
	var bike: Vehicle = null
	for v in Vehicle.all:
		if v.owned:
			bike = v
	log_t("house bike: " + (("%s at %s" % [bike.spec["name"], str(bike.global_position)]) if bike else "none"))
	if bike:
		p.enter_vehicle(bike)
		await wait(1.0)
		Hud.s_gas = true
		await wait(1.6)
		log_t("bike speed %d km/h, riding %s" % [int(bike.speed() * 3.6), str(p.vehicle == bike)])
		await snap("07-bike")
		Hud.s_gas = false
		await wait(1.5)
		p.exit_vehicle()
	await wait(1.0)
	g.cheat("8080")
	await wait(1.0)
	var car: Vehicle = null
	var cd := 40.0 * 40.0
	for v in Vehicle.all:
		if v.spec["name"] == "sports_car" and v.driver == null and v.global_position.distance_squared_to(p.global_position) < cd:
			cd = v.global_position.distance_squared_to(p.global_position)
			car = v
	if car:
		log_t("cheat car at %s" % str(car.global_position))
		p.enter_vehicle(car)
	Hud.s_gas = true
	await wait(3.0)
	log_t("car: " + (("%s %d km/h, grounded %s" % [p.vehicle.spec["name"], int(p.vehicle.speed() * 3.6), str(p.vehicle.grounded)]) if p.vehicle else "not in a car"))
	await snap("08-car")
	Hud.s_gas = false
	await wait(1.0)
	if p.vehicle:
		p.exit_vehicle()
	for pt in G.city.points:
		if "Ujjayanta" in pt["name"]:
			g.test_teleport(pt["p"] + Vector3(0, 0.3, 60), 0.0)
			G.cam.yaw = 0.0
			G.cam.pitch = 8.0
			await wait(4.0)
			await snap("09-palace")
			break
	G.menus.big_map()
	await wait(1.0)
	await snap("10-map")
	G.menus.close()
	G.menus.gun_shop()
	await wait(1.0)
	await snap("11-gunshop")
	G.menus.close()
	var jetty: Dictionary = G.city.point("boat")
	if not jetty.is_empty():
		g.test_teleport(jetty["p"] + Vector3.UP * 1.2, jetty["yaw"])
		await wait(3.0)
		g.cheat("5050")
		await wait(1.0)
		var boat: Vehicle = null
		var bd := 1e9
		for v in Vehicle.all:
			if v.is_boat() and v.global_position.distance_squared_to(p.global_position) < bd:
				bd = v.global_position.distance_squared_to(p.global_position)
				boat = v
		if boat:
			p.enter_vehicle(boat)
			Hud.s_gas = true
			await wait(4.0)
			log_t("boat %d km/h at %s, in boat %s" % [int(boat.speed() * 3.6), str(boat.global_position), str(p.vehicle == boat)])
			await snap("12-boat")
			Hud.s_gas = false
			p.exit_vehicle(true)
	var hp: Vector3 = g.spawn_point()
	for pt in G.city.points:
		if pt["kind"] == "helipad":
			hp = pt["p"]
	g.test_teleport(hp + Vector3(8, 0.5, 0), 0.0)
	await wait(2.0)
	g.cheat("9090")
	await wait(1.0)
	for v in Vehicle.all:
		if v.is_heli() and v.driver == null and v.global_position.distance_squared_to(p.global_position) < 900.0:
			p.enter_vehicle(v)
			break
	await wait(3.0)
	Hud.s_up = true
	await wait(5.0)
	Hud.s_up = false
	Hud.s_move = Vector2(0, 0.6)
	await wait(2.0)
	if p.vehicle:
		log_t("heli %d km/h, height %.1f m" % [int(p.vehicle.speed() * 3.6), p.vehicle.global_position.y - hp.y])
	else:
		log_t("heli: not in a helicopter")
	await snap("13-heli")
	Hud.s_move = Vector2.ZERO
	if p.vehicle:
		p.exit_vehicle(true)
	g.test_teleport(g.spawn_point(), 0.0)
	G.env.hour = 21.0
	await wait(3.0)
	await snap("14-night")
	G.env.hour = 10.0
	Wanted.set_stars(3)
	await wait(8.0)
	await snap("15-police")
	Wanted.set_stars(0)
	Hud.scripted = false
	log_t("DONE")
	if out_dir != "":
		get_tree().quit()
