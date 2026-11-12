class_name LevelBuilder
extends RefCounted
## Turns a LevelData (ordered chunks) into a playable level: TileMapLayer terrain,
## hazards, platforms, pickups, enemies, checkpoints, decorations.

const T := 64
const ROWS := 26
const PIT_Y := 22 * 64   # falling below this line counts as a pit fall
const ATLAS := "res://assets/environments/tiles/terrain_atlas.png"
const PROPS := "res://assets/environments/props/"
const TUTORIAL_HINTS := [
	"Drag the joystick to run.\nTap JUMP to leap over gaps!",
	"Tap the SWORD to slash enemies.\nJump on slimes to squash them!",
]
# atlas columns
const C_TL := 0
const C_T := 1
const C_TR := 2
const C_L := 3
const C_C := 4
const C_R := 5
const C_BL := 6
const C_B := 7
const C_BR := 8
const C_SINGLE := 9
const C_HL := 10
const C_HM := 11
const C_HR := 12
const C_CL := 13
const C_CM := 14
const C_CR := 15

var level: LevelData
var world: Dictionary
var grid: Array = []          # Array[PackedStringArray rows] -> grid[y][x]
var width := 0
var rng := RandomNumberGenerator.new()

# outputs
var root: Node2D
var terrain: TileMapLayer
var oneway: TileMapLayer
var decor: Node2D
var entities: Node2D
var player_start := Vector2(128, 1000)
var checkpoints: Array = []
var exit_gate: ExitGate
var boss_spawn := Vector2.ZERO
var arena_left := -1.0
var arena_right := -1.0
var total_coins := 0
var breakables: Array = []
var enemies: Array = []
var lights: Array = []
var _hint := 0
var pending_enemies: Array = []


func build(p_level: LevelData, p_root: Node2D) -> void:
	level = p_level
	world = GameData.world(level.world)
	root = p_root
	rng.seed = level.index * 7919 + 17
	_compose_grid()
	terrain = TileMapLayer.new()
	terrain.name = "Terrain"
	terrain.tile_set = _make_tileset()
	terrain.collision_enabled = true
	oneway = TileMapLayer.new()
	oneway.name = "OneWay"
	oneway.tile_set = terrain.tile_set
	decor = Node2D.new()
	decor.name = "Decor"
	decor.z_index = -1
	entities = Node2D.new()
	entities.name = "Entities"
	root.add_child(decor)
	root.add_child(terrain)
	root.add_child(oneway)
	root.add_child(entities)
	_place_tiles()
	_place_entities()
	_place_decor()
	_place_bounds()


func size_px() -> Vector2:
	return Vector2(width * T, ROWS * T)


# ----------------------------------------------------------------- grid
func _compose_grid() -> void:
	grid.clear()
	for y in ROWS:
		grid.append([])
	for name in level.chunks:
		var rows: Array = ChunkLibrary.CHUNKS.get(name, ChunkLibrary.CHUNKS["flat_coins"])
		var w: int = rows[0].length()
		var top := 19 - rows.size()
		for y in ROWS:
			for x in w:
				var ch := "."
				if y >= top and y <= 18:
					ch = rows[y - top][x]
				elif y > 18:
					var last: String = rows[rows.size() - 1][x]
					ch = "#" if (last == "#" or last == "^") else ("L" if last == "L" else ".")
				grid[y].append(ch)
		width += w


func cell(x: int, y: int) -> String:
	if y >= ROWS:
		return "#"
	if x < 0 or x >= width or y < 0:
		return "#" if y >= 0 and (x < 0 or x >= width) else "."
	return grid[y][x]


func _is_solid(x: int, y: int) -> bool:
	var c := cell(x, y)
	return c == "#" or c == "X"


func cell_pos(x: int, y: int) -> Vector2:
	return Vector2(x * T + T / 2.0, y * T + T / 2.0)


# -------------------------------------------------------------- tileset
func _make_tileset() -> TileSet:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(T, T)
	ts.add_physics_layer()
	ts.set_physics_layer_collision_layer(0, 1)
	ts.set_physics_layer_collision_mask(0, 0)
	var src := TileSetAtlasSource.new()
	src.texture = SpriteLib.tex(ATLAS)
	src.texture_region_size = Vector2i(T, T)
	ts.add_source(src, 0)
	var full := PackedVector2Array([Vector2(-32, -32), Vector2(32, -32), Vector2(32, 32), Vector2(-32, 32)])
	var slab := PackedVector2Array([Vector2(-32, -30), Vector2(32, -30), Vector2(32, 10), Vector2(-32, 10)])
	var cloud := PackedVector2Array([Vector2(-32, -26), Vector2(32, -26), Vector2(32, -4), Vector2(-32, -4)])
	for row in 6:
		for col in 16:
			var ac := Vector2i(col, row)
			src.create_tile(ac)
			var td := src.get_tile_data(ac, 0)
			td.add_collision_polygon(0)
			if col >= C_CL:
				td.set_collision_polygon_points(0, 0, cloud)
				td.set_collision_polygon_one_way(0, 0, true)
			elif col >= C_HL:
				td.set_collision_polygon_points(0, 0, slab)
			else:
				td.set_collision_polygon_points(0, 0, full)
	return ts


func _place_tiles() -> void:
	var row: int = world.terrain
	for y in ROWS:
		for x in width:
			var c := cell(x, y)
			if c == "#":
				terrain.set_cell(Vector2i(x, y), 0, Vector2i(_auto_col(x, y), row))
			elif c == "=":
				var l := cell(x - 1, y) == "="
				var r := cell(x + 1, y) == "="
				var col := C_CM
				if not l and r:
					col = C_CL
				elif l and not r:
					col = C_CR
				elif not l and not r:
					col = C_CM
				oneway.set_cell(Vector2i(x, y), 0, Vector2i(col, row))


func _auto_col(x: int, y: int) -> int:
	var up := _is_solid(x, y - 1)
	var down := _is_solid(x, y + 1)
	var left := _is_solid(x - 1, y)
	var right := _is_solid(x + 1, y)
	if not up and not down:
		if left and right:
			return C_HM
		if right:
			return C_HL
		if left:
			return C_HR
		return C_SINGLE
	if not up:
		if left and right:
			return C_T
		if right:
			return C_TL
		if left:
			return C_TR
		return C_SINGLE
	if not down:
		if left and right:
			return C_B
		if right:
			return C_BL
		if left:
			return C_BR
		return C_C
	if left and right:
		return C_C
	if right:
		return C_L
	if left:
		return C_R
	return C_C


func _atlas_region_tex(col: int) -> AtlasTexture:
	var at := AtlasTexture.new()
	at.atlas = SpriteLib.tex(ATLAS)
	at.region = Rect2(col * T, int(world.terrain) * T, T, T)
	return at


# ------------------------------------------------------------- entities
func _sprite(tex_name: String, pos: Vector2, parent: Node = null, z := 0) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = SpriteLib.tex(PROPS + tex_name + ".png")
	s.position = pos
	s.z_index = z
	(parent if parent else entities).add_child(s)
	return s


func _place_entities() -> void:
	var water := int(level.world) <= 3
	var cp_index := 0
	var visited_l := {}
	var visited_h := {}
	for y in ROWS:
		for x in width:
			var c := cell(x, y)
			var p := cell_pos(x, y)
			match c:
				"P":
					player_start = Vector2(p.x, (y + 1) * T)
				"C":
					var cp := Checkpoint.create(cp_index)
					cp.position = Vector2(p.x, (y + 1) * T - 40)
					entities.add_child(cp)
					checkpoints.append(cp)
					cp_index += 1
				"E":
					exit_gate = ExitGate.create(level.boss_id != "")
					exit_gate.position = Vector2(p.x, (y + 1) * T - 32)
					entities.add_child(exit_gate)
				"O":
					boss_spawn = Vector2(p.x, (y + 1) * T)
					_find_arena(x)
				"o":
					_add_pickup("coin", p)
				"g":
					_add_pickup("gem", p)
				"+":
					_add_pickup("heart", p)
				"1", "2", "3", "4", "5", "6":
					_add_powerup(int(c) - 1, p)
				"!":
					_add_powerup(rng.randi_range(1, 5), p)
				"T":
					var chest := Breakable.create("chest", SpriteLib.tex(PROPS + "chest_closed.png"))
					chest.position = Vector2(p.x, (y + 1) * T - 28)
					chest.coins_inside = 12 + int(level.difficulty * 4)
					entities.add_child(chest)
					breakables.append(chest)
				"B":
					var crate := Breakable.create("crate", SpriteLib.tex(PROPS + "block_planks.png"))
					crate.position = p
					entities.add_child(crate)
					breakables.append(crate)
				"?":
					var blk := Breakable.create("coin_block", SpriteLib.tex(PROPS + "block_coin.png"))
					blk.position = p
					entities.add_child(blk)
					breakables.append(blk)
					total_coins += 3
				"X":
					var wall := Breakable.create("secret", _atlas_region_tex(_auto_col(x, y)))
					wall.position = p
					entities.add_child(wall)
					breakables.append(wall)
				"J":
					var sp := LevelProps.Spring.new()
					sp.position = p
					entities.add_child(sp)
				"Z":
					var saw := LevelProps.Saw.new()
					saw.position = p + Vector2(0, 6)
					saw.damage = 18.0 + level.difficulty * 4.0
					entities.add_child(saw)
				"W":
					var cr := LevelProps.Crusher.new()
					var drop_rows := 0
					while drop_rows < 12 and not _is_solid(x, y + drop_rows + 1):
						drop_rows += 1
					cr.position = p
					cr.drop = max(0, drop_rows * T - 13)
					entities.add_child(cr)
				"M":
					var mp := MovingPlatform.create(SpriteLib.tex(ATLAS), world.terrain, Vector2(4 * T, 0), 3.6)
					mp.position = p
					entities.add_child(mp)
				"V":
					var vp := MovingPlatform.create(SpriteLib.tex(ATLAS), world.terrain, Vector2(0, 3 * T), 3.2)
					vp.position = p
					entities.add_child(vp)
				"F":
					var fp := FallingPlatform.create(SpriteLib.tex(PROPS + "bridge_logs.png"))
					fp.position = p
					entities.add_child(fp)
				"^":
					var spk := _sprite("spikes", p)
					spk.z_index = 1
					var hz := HazardZone.create(Rect2(p.x - 28, p.y, 56, 30), 20.0 + level.difficulty * 3.0, y >= 18)
					entities.add_child(hz)
				"L":
					if not visited_l.has(Vector2i(x, y)):
						_place_liquid_run(x, y, water, visited_l)
				"H":
					if not visited_h.has(Vector2i(x, y)):
						_place_ladder(x, y, visited_h)
				"t":
					_add_torch(p)
				"I":
					var sign := LevelProps.HintSign.new()
					sign.text = TUTORIAL_HINTS[_hint % TUTORIAL_HINTS.size()]
					_hint += 1
					sign.position = Vector2(p.x, (y + 1) * T - 32)
					entities.add_child(sign)
				"a", "b", "c", "d":
					_queue_enemy(_pick_enemy(c), x, y)
				"h":
					_queue_enemy("fish", x, y)
				"n":
					_queue_enemy("barnacle", x, y)


func _find_arena(boss_x: int) -> void:
	# walls of the arena chunk: nearest wall columns left/right of the boss at row 5
	var lx := boss_x
	while lx > 0 and cell(lx, 6) != "#":
		lx -= 1
	var rx := boss_x
	while rx < width - 1 and cell(rx, 6) != "#":
		rx += 1
	arena_left = lx * T + T
	arena_right = rx * T


func _queue_enemy(id: String, x: int, y: int) -> void:
	if id == "":
		return
	pending_enemies.append({"id": id, "pos": Vector2(x * T + T / 2.0, (y + 1) * T)})


func _pick_enemy(slot: String) -> String:
	for entry in level.enemy_pool:
		var parts: PackedStringArray = entry.split(":")
		if parts.size() == 2 and parts[0] == slot:
			var opts: PackedStringArray = parts[1].split(",")
			return opts[rng.randi_range(0, opts.size() - 1)]
	return "slime"


func _add_pickup(kind: String, pos: Vector2) -> void:
	var tex_name: String = {"coin": "coin_gold", "gem": "gem_blue", "heart": "heart"}[kind]
	if kind == "gem":
		tex_name = ["gem_blue", "gem_green", "gem_red", "gem_yellow"][rng.randi_range(0, 3)]
	var pk := Pickup.create(kind, SpriteLib.tex(PROPS + tex_name + ".png"), 1)
	pk.position = pos
	entities.add_child(pk)
	if kind == "coin":
		total_coins += 1


func _add_powerup(idx: int, pos: Vector2) -> void:
	var data: PowerupData = GameData.powerups[clampi(idx, 0, GameData.powerups.size() - 1)]
	var pk := Pickup.create("powerup", data.icon, 1, data.id)
	pk.sprite.modulate = data.color
	pk.position = pos
	entities.add_child(pk)


func _place_liquid_run(x0: int, y: int, water: bool, visited: Dictionary) -> void:
	var x1 := x0
	while cell(x1 + 1, y) == "L":
		x1 += 1
	var base := "water" if water else "lava"
	for x in range(x0, x1 + 1):
		visited[Vector2i(x, y)] = true
		var top := cell(x, y - 1) != "L"
		var s := _sprite(base + ("_top" if top else ""), cell_pos(x, y), decor)
		s.z_index = 2
		if not water:
			s.modulate = Color(1.15, 1.05, 1.0)
		if top:
			var low := SpriteLib.tex(PROPS + base + "_top_low.png")
			var high := s.texture
			var tw := s.create_tween().set_loops()
			tw.tween_interval(0.35 + (x % 3) * 0.05)
			tw.tween_callback(func(): s.texture = low)
			tw.tween_interval(0.35)
			tw.tween_callback(func(): s.texture = high)
			if not water and x % 3 == 0:
				lights.append([cell_pos(x, y), Color(1, 0.45, 0.1, 0.35), 2.2])
	if cell(x0, y - 1) != "L":
		var hz := HazardZone.create(Rect2(x0 * T, y * T + 18, (x1 - x0 + 1) * T, T * 4), 25.0, true)
		entities.add_child(hz)


func _place_ladder(x: int, y0: int, visited: Dictionary) -> void:
	var y1 := y0
	while cell(x, y1 + 1) == "H":
		y1 += 1
	for y in range(y0, y1 + 1):
		visited[Vector2i(x, y)] = true
		var tex := "ladder_middle"
		if y == y0:
			tex = "ladder_top"
		elif y == y1:
			tex = "ladder_bottom"
		_sprite(tex, cell_pos(x, y), decor)
	var lad := LevelProps.Ladder.new()
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(36, (y1 - y0 + 1) * T + 40)
	cs.shape = r
	lad.add_child(cs)
	lad.position = Vector2(x * T + T / 2.0, (y0 + y1 + 1) * T / 2.0 - 20)
	lad.set_meta("top_y", y0 * T)
	entities.add_child(lad)
	# standable top of the ladder
	var top := StaticBody2D.new()
	top.collision_layer = 1
	var tcs := CollisionShape2D.new()
	var tr := RectangleShape2D.new()
	tr.size = Vector2(64, 12)
	tcs.shape = tr
	tcs.one_way_collision = true
	top.add_child(tcs)
	top.position = Vector2(x * T + T / 2.0, y0 * T + 6)
	entities.add_child(top)


func _add_torch(pos: Vector2) -> void:
	var s := _sprite("torch_on_a", pos, decor)
	var a := SpriteLib.tex(PROPS + "torch_on_a.png")
	var b := SpriteLib.tex(PROPS + "torch_on_b.png")
	var tw := s.create_tween().set_loops()
	tw.tween_interval(0.18)
	tw.tween_callback(func(): s.texture = b)
	tw.tween_interval(0.18)
	tw.tween_callback(func(): s.texture = a)
	lights.append([pos + Vector2(0, -16), Color(1, 0.6, 0.25, 0.55), 1.8])


# --------------------------------------------------------------- decor
func _place_decor() -> void:
	var options: Array = world.decor
	var sway := preload("res://shaders/sway.gdshader")
	for x in range(1, width - 1):
		for y in range(1, ROWS - 1):
			if cell(x, y) != "." or not _is_solid(x, y + 1):
				continue
			if rng.randf() > 0.22:
				continue
			var pick: String = options[rng.randi_range(0, options.size() - 1)]
			if pick == "torch_on_a":
				_add_torch(cell_pos(x, y))
				continue
			var s := _sprite(pick, cell_pos(x, y), decor)
			s.z_index = -1
			if pick in ["bush", "grass", "grass_purple", "mushroom_red", "mushroom_brown", "cactus"]:
				var m := ShaderMaterial.new()
				m.shader = sway
				m.set_shader_parameter("phase", rng.randf() * 6.0)
				m.set_shader_parameter("strength", 5.0 if pick != "cactus" else 1.5)
				s.material = m
			if pick == "snow":
				s.position.y += 6
	# world light sources around coins of the dark worlds are added by Game


func _place_bounds() -> void:
	for side in [-1, 1]:
		var wall := StaticBody2D.new()
		wall.collision_layer = 1
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(64, ROWS * T * 3)
		cs.shape = r
		wall.add_child(cs)
		wall.position = Vector2(-32 if side < 0 else width * T + 32, ROWS * T / 2.0 - ROWS * T)
		root.add_child(wall)
