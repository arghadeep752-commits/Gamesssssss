class_name Wanted
extends RefCounted
## Stars, heat and the police response.

const LEVELS := [0.0, 0.8, 3.0, 6.0, 10.0, 15.0]
static var stars := 0
static var heat := 0.0
static var last_seen := 0.0
static var never := false


static func crime(h: float, _at: Vector3, cop := false) -> void:
	if never or G.game == null or G.game.state != G.game.S.PLAY:
		return
	heat += h * (1.5 if cop else 1.0)
	var s := 0
	for i in range(1, LEVELS.size()):
		if heat >= LEVELS[i]:
			s = i
	if s > stars:
		stars = s
		Hud.stars_changed()
	last_seen = G.now


static func noise(at: Vector3, shooter: Human) -> void:
	Traffic.panic(at, 32.0)
	if shooter and shooter.is_player:
		crime(0.15, at, cops_near(at, 40.0))


static func seen() -> void:
	last_seen = G.now


static func cops_near(p: Vector3, r: float) -> bool:
	var r2 := r * r
	for h in Human.all:
		if h.police and not h.dead and h.global_position.distance_squared_to(p) < r2:
			return true
	for v in Vehicle.all:
		if v.spec["police"] and v.npc_driver and v.global_position.distance_squared_to(p) < r2:
			return true
	return false


static func tick() -> void:
	if stars == 0:
		heat = maxf(0.0, heat - G.dt * 0.05)
		return
	if cops_near(Player.I.global_position, 25.0):
		last_seen = G.now
	if G.now - last_seen > 18.0 + stars * 6.0:
		stars -= 1
		heat = LEVELS[stars]
		last_seen = G.now
		Hud.stars_changed()


static func escape() -> float:
	return 0.0 if stars == 0 else clampf((G.now - last_seen) / (18.0 + stars * 6.0), 0.0, 1.0)


static func set_stars(s: int) -> void:
	stars = clampi(s, 0, 5)
	heat = LEVELS[stars]
	last_seen = G.now
	Hud.stars_changed()
