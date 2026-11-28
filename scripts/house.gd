extends Node3D
## Builds Scary Aunty's 3 floor house: walls, floors, stairs, windows, doors,
## furniture, lights, reflection probes, puzzle objects and the AI waypoints.
##
## Map (same on every floor, seen from above, x to the right, z downwards):
##   z 0..4   : D (bathroom) | E (store) | STAIRS (x 10..18)
##   z 4..6   : corridor (front door on the ground floor at x = 0)
##   z 6..14  : A | B | C   (big rooms)
## Floors: 0 = ground (y 0), 1 = middle (y 3), 2 = top (y 6).

const DoorScript = preload("res://scripts/door.gd")
const InteractScript = preload("res://scripts/interactable.gd")
const FallbackScript = preload("res://scripts/fallback.gd")

const FH := 3.0
const SLAB := 0.2
const EXT_T := 0.25
const INT_T := 0.15
const DOOR_W := 1.0
const DOOR_H := 2.2
const HX := 18.0
const HZ := 14.0
const WIN_SILL := 0.9
const WIN_TOP := 2.1

## How many metres one texture repeat covers.
const TILE := {"wall": 2.5, "floor": 2.0, "ceiling": 3.0, "wood": 1.2, "lamp": 1.0, "glass": 1.0}

## Object sizes: width (x), height (y), depth (z). Front of a model faces +Z.
const SIZES := {
	"sofa": Vector3(2.0, 0.85, 0.9),
	"tv_cabinet": Vector3(1.4, 0.5, 0.45),
	"tv": Vector3(1.0, 0.62, 0.25),
	"coffee_table": Vector3(1.0, 0.45, 0.6),
	"plant": Vector3(0.5, 1.1, 0.5),
	"kitchen_counter": Vector3(2.0, 0.9, 0.62),
	"stove": Vector3(0.7, 0.9, 0.62),
	"fridge": Vector3(0.75, 1.8, 0.7),
	"dining_table": Vector3(1.4, 0.78, 0.9),
	"chair": Vector3(0.45, 0.92, 0.48),
	"bookshelf": Vector3(1.0, 2.0, 0.38),
	"shelf": Vector3(1.0, 1.8, 0.4),
	"toilet": Vector3(0.42, 0.78, 0.7),
	"sink": Vector3(0.55, 0.9, 0.45),
	"washing_machine": Vector3(0.6, 0.85, 0.6),
	"cardboard_box": Vector3(0.55, 0.45, 0.55),
	"bed_double": Vector3(1.6, 0.6, 2.05),
	"bed_single": Vector3(1.0, 0.55, 2.0),
	"wardrobe": Vector3(1.2, 2.0, 0.6),
	"dressing_table": Vector3(1.0, 1.5, 0.45),
	"nightstand": Vector3(0.45, 0.55, 0.4),
	"desk": Vector3(1.2, 0.76, 0.6),
	"safe": Vector3(0.6, 0.75, 0.6),
	"school_bag": Vector3(0.35, 0.42, 0.2),
	"sideboard": Vector3(1.6, 0.9, 0.45),
	"key_old": Vector3(0.12, 0.02, 0.05),
	"key_gold": Vector3(0.14, 0.02, 0.06),
	"hammer": Vector3(0.35, 0.05, 0.13),
	"bolt_cutter": Vector3(0.6, 0.05, 0.12),
	"padlock": Vector3(0.12, 0.15, 0.05),
	"chain": Vector3(0.9, 0.08, 0.08),
	"planks": Vector3(1.25, 0.17, 0.035),
}

const ITEM_MODEL := {"room_key": "key_old", "hammer": "hammer", "bolt_cutter": "bolt_cutter", "main_key": "key_gold"}

## [floor, model, x, z, facing (0 = +Z, 180 = -Z, 90 = +X, -90 = -X), optional "on:<model>"]
const FURNITURE := [
	# ---- Ground floor
	[0, "sofa", 0.62, 10.0, 90],
	[0, "tv_cabinet", 5.67, 10.0, -90],
	[0, "tv", 5.7, 10.0, -90, "on:tv_cabinet"],
	[0, "coffee_table", 2.4, 10.0, 90],
	[0, "plant", 5.4, 13.4, 0],
	[0, "plant", 0.6, 6.7, 0],
	[0, "kitchen_counter", 8.0, 13.52, 180],
	[0, "stove", 9.42, 13.52, 180],
	[0, "fridge", 11.53, 12.3, -90],
	[0, "dining_table", 8.6, 10.0, 0],
	[0, "chair", 8.6, 9.25, 0],
	[0, "chair", 8.6, 10.75, 180],
	[0, "dining_table", 15.0, 11.0, 0],
	[0, "chair", 15.0, 10.25, 0],
	[0, "chair", 15.0, 11.75, 180],
	[0, "sideboard", 15.0, 13.6, 180],
	[0, "bookshelf", 17.68, 8.5, -90],
	[0, "plant", 12.6, 13.4, 0],
	[0, "toilet", 4.4, 0.53, 0],
	[0, "sink", 0.36, 1.8, 90],
	[0, "washing_machine", 9.55, 0.43, 0],
	[0, "shelf", 5.3, 2.0, 90],
	[0, "cardboard_box", 8.3, 0.45, 0],
	[0, "cardboard_box", 7.6, 0.5, 15],
	# ---- Middle floor
	[1, "bed_double", 3.0, 12.8, 180],
	[1, "nightstand", 1.6, 13.6, 180],
	[1, "nightstand", 4.4, 13.6, 180],
	[1, "wardrobe", 5.6, 9.0, -90],
	[1, "dressing_table", 0.37, 7.5, 90],
	[1, "chair", 9.0, 12.8, 0],
	[1, "bookshelf", 11.68, 10.0, -90],
	[1, "bed_single", 16.9, 12.8, 180],
	[1, "wardrobe", 12.4, 9.0, 90],
	[1, "chair", 14.0, 13.4, 180],
	[1, "plant", 17.4, 6.7, 0],
	[1, "toilet", 4.4, 0.53, 0],
	[1, "sink", 0.36, 1.8, 90],
	[1, "cardboard_box", 9.4, 0.5, 0],
	[1, "cardboard_box", 9.4, 1.15, 10],
	[1, "cardboard_box", 6.0, 0.5, 30],
	[1, "shelf", 5.3, 2.0, 90],
	# ---- Top floor
	[2, "bed_single", 0.66, 11.0, 180],
	[2, "desk", 5.6, 11.5, -90],
	[2, "chair", 4.95, 11.5, 90],
	[2, "school_bag", 4.6, 13.5, 160],
	[2, "wardrobe", 5.6, 8.2, -90],
	[2, "cardboard_box", 6.6, 13.4, 0],
	[2, "cardboard_box", 7.3, 13.4, 10],
	[2, "cardboard_box", 6.6, 12.7, 30],
	[2, "shelf", 11.68, 10.0, -90],
	[2, "chair", 10.5, 13.3, 200],
	[2, "bed_single", 16.9, 12.8, 180],
	[2, "sideboard", 12.3, 10.0, 90],
	[2, "chair", 14.5, 12.5, 160],
	[2, "toilet", 4.4, 0.53, 0],
	[2, "sink", 0.36, 1.8, 90],
	[2, "cardboard_box", 9.4, 0.5, 0],
	[2, "cardboard_box", 8.7, 0.45, 20],
	[2, "cardboard_box", 9.4, 1.15, 45],
	[2, "shelf", 5.3, 2.0, 90],
]

## Room doors: room -> [door x, point just inside the room (x, z)]
const ROOM_DOORS := {
	"A": [3.0, 3.0, 6.9],
	"B": [9.0, 9.0, 6.9],
	"C": [15.0, 15.0, 6.9],
	"D": [2.5, 2.5, 3.1],
	"E": [7.5, 7.5, 3.1],
}
## Patrol points inside each room, per floor (kept away from furniture).
const ROOM_PATROL := [
	{"A": [Vector2(4.0, 8.2), Vector2(3.8, 12.3)], "B": [Vector2(7.0, 7.8), Vector2(10.6, 8.0), Vector2(10.6, 11.0)],
		"C": [Vector2(13.3, 8.0), Vector2(16.6, 10.5)], "D": [Vector2(2.5, 1.8)], "E": [Vector2(7.5, 2.0)]},
	{"A": [Vector2(3.0, 8.3), Vector2(1.4, 10.5)], "B": [Vector2(9.0, 9.5), Vector2(8.0, 11.5)],
		"C": [Vector2(15.0, 8.5), Vector2(14.8, 11.5)], "D": [Vector2(2.5, 1.8)], "E": [Vector2(7.5, 2.0)]},
	{"A": [Vector2(3.0, 8.5), Vector2(3.0, 12.0)], "B": [Vector2(9.0, 9.0), Vector2(8.0, 11.8)],
		"C": [Vector2(15.0, 8.5), Vector2(14.6, 10.8)], "D": [Vector2(2.5, 1.8)], "E": [Vector2(7.5, 2.2)]},
]

const NOTE_TEXT := "Note to myself:\n\nI wrote my safe code in CHALK on the walls of my house, so I never forget it.\n\nThe order is:\nRED  -  BLUE  -  GREEN  -  YELLOW\n\n- Aunty"

const CHALK_COLORS := [Color(0.95, 0.22, 0.2), Color(0.35, 0.6, 1.0), Color(0.35, 0.92, 0.38), Color(1.0, 0.9, 0.3)]

var game
var fb
var floor_nodes: Array = []
var batches: Array = []
var bodies: Array = []
var shadow_list: Array = []
var doors: Array = []
var room_doors := {}
var astar := AStar3D.new()
var wp_floor := {}
var patrol_points: Array = []
var spawn_player := Vector3(2.6, 6.05, 10.8)
var spawn_player_yaw := 0.0
var spawn_aunty := Vector3(7.0, 0.05, 8.0)
var start_door
var study_door
var front_door
var safe_body
var safe_node: Node3D
var front_locks := {}
var exterior_root: Node3D
var probes_root: Node3D
var _next_wp := 1


func layer_of(f: int) -> int:
	return 1 << (f + 1)


func build(code: Array) -> void:
	fb = FallbackScript.new()
	exterior_root = Node3D.new()
	exterior_root.name = "Outside"
	add_child(exterior_root)
	probes_root = Node3D.new()
	probes_root.name = "ReflectionProbes"
	add_child(probes_root)
	for f in range(3):
		var n := Node3D.new()
		n.name = "Floor%d" % f
		add_child(n)
		floor_nodes.append(n)
		batches.append({})
		var body := StaticBody3D.new()
		body.name = "Collision"
		body.collision_layer = 1
		body.collision_mask = 0
		n.add_child(body)
		bodies.append(body)
	for f in range(3):
		_build_structure(f)
	_build_stairs()
	_build_roof_and_ground()
	for f in range(3):
		_build_lights_and_probes(f)
	_build_doors()
	_build_furniture()
	_build_puzzle(code)
	_build_waypoints()
	for f in range(3):
		_commit_batches(f)
	_commit_shadow_proxy()


# ================================================================ geometry helpers

## Adds a box to the floor's merged mesh (one draw call per material).
func _box(f: int, slot: String, center: Vector3, size: Vector3, collide: bool = true) -> void:
	var groups: Dictionary = batches[f]
	if not groups.has(slot):
		groups[slot] = []
	groups[slot].append([center, size])
	if collide:
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		cs.shape = shape
		cs.position = center
		bodies[f].add_child(cs)
		if slot != "glass":
			shadow_list.append([center, size])


func _rect_minus(r: Rect2, h: Rect2) -> Array:
	var out: Array = []
	if h.position.x > r.position.x:
		out.append(Rect2(r.position.x, r.position.y, h.position.x - r.position.x, r.size.y))
	if r.end.x > h.end.x:
		out.append(Rect2(h.end.x, r.position.y, r.end.x - h.end.x, r.size.y))
	if h.position.y > r.position.y:
		out.append(Rect2(h.position.x, r.position.y, h.size.x, h.position.y - r.position.y))
	if r.end.y > h.end.y:
		out.append(Rect2(h.position.x, h.end.y, h.size.x, r.end.y - h.end.y))
	return out


## Floor areas of a floor (with the stair holes cut out). f = 3 means the roof.
func _floor_rects(f: int) -> Array:
	var out: Array = [Rect2(0, 6, 6, 8), Rect2(6, 6, 6, 8), Rect2(12, 6, 6, 8), Rect2(0, 0, 5, 4), Rect2(5, 0, 5, 4), Rect2(0, 4, 18, 2)]
	var stair := Rect2(10, 0, 8, 4)
	if f == 1:
		out.append_array(_rect_minus(stair, Rect2(12.0, 0.15, 4.5, 1.2)))
	elif f == 2:
		out.append_array(_rect_minus(stair, Rect2(12.0, 1.5, 4.5, 1.2)))
	else:
		out.append(stair)
	return out


## Wall running along X at depth z. openings = [[from_x, to_x, bottom, top], ...]
func _wall_x(f: int, z: float, x0: float, x1: float, t: float, openings: Array) -> void:
	var y0 := f * FH
	var ops := openings.duplicate()
	ops.sort_custom(func(p, q): return p[0] < q[0])
	var cur := x0
	for o in ops:
		var a: float = o[0]
		var b: float = o[1]
		var bottom: float = o[2]
		var top: float = o[3]
		if a > cur + 0.001:
			_box(f, "wall", Vector3((cur + a) * 0.5, y0 + FH * 0.5, z), Vector3(a - cur, FH, t))
		if top < FH:
			_box(f, "wall", Vector3((a + b) * 0.5, y0 + (top + FH) * 0.5, z), Vector3(b - a, FH - top, t))
		if bottom > 0.001:
			_box(f, "wall", Vector3((a + b) * 0.5, y0 + bottom * 0.5, z), Vector3(b - a, bottom, t))
			_window(f, Vector3((a + b) * 0.5, y0, z), b - a, t, true)
		cur = b
	if x1 > cur + 0.001:
		_box(f, "wall", Vector3((cur + x1) * 0.5, y0 + FH * 0.5, z), Vector3(x1 - cur, FH, t))


## Wall running along Z at x.
func _wall_z(f: int, x: float, z0: float, z1: float, t: float, openings: Array) -> void:
	var y0 := f * FH
	var ops := openings.duplicate()
	ops.sort_custom(func(p, q): return p[0] < q[0])
	var cur := z0
	for o in ops:
		var a: float = o[0]
		var b: float = o[1]
		var bottom: float = o[2]
		var top: float = o[3]
		if a > cur + 0.001:
			_box(f, "wall", Vector3(x, y0 + FH * 0.5, (cur + a) * 0.5), Vector3(t, FH, a - cur))
		if top < FH:
			_box(f, "wall", Vector3(x, y0 + (top + FH) * 0.5, (a + b) * 0.5), Vector3(t, FH - top, b - a))
		if bottom > 0.001:
			_box(f, "wall", Vector3(x, y0 + bottom * 0.5, (a + b) * 0.5), Vector3(t, bottom, b - a))
			_window(f, Vector3(x, y0, (a + b) * 0.5), b - a, t, false)
		cur = b
	if z1 > cur + 0.001:
		_box(f, "wall", Vector3(x, y0 + FH * 0.5, (cur + z1) * 0.5), Vector3(t, FH, z1 - cur))


## Glass pane + wooden sill / top / middle bar.
func _window(f: int, base: Vector3, width: float, t: float, along_x: bool) -> void:
	var h := WIN_TOP - WIN_SILL
	var c := base + Vector3(0, WIN_SILL + h * 0.5, 0)
	if along_x:
		_box(f, "glass", c, Vector3(width, h, 0.02))
		_box(f, "wood", base + Vector3(0, WIN_SILL + 0.03, 0), Vector3(width, 0.06, t + 0.08), false)
		_box(f, "wood", base + Vector3(0, WIN_TOP - 0.03, 0), Vector3(width, 0.06, t + 0.02), false)
		_box(f, "wood", c, Vector3(0.05, h, 0.06), false)
	else:
		_box(f, "glass", c, Vector3(0.02, h, width))
		_box(f, "wood", base + Vector3(0, WIN_SILL + 0.03, 0), Vector3(t + 0.08, 0.06, width), false)
		_box(f, "wood", base + Vector3(0, WIN_TOP - 0.03, 0), Vector3(t + 0.02, 0.06, width), false)
		_box(f, "wood", c, Vector3(0.06, h, 0.05), false)


# ================================================================ structure

func _build_structure(f: int) -> void:
	var y0 := f * FH
	# Floors (top surface at y0) and the ceiling under the next floor.
	for r in _floor_rects(f):
		_box(f, "floor", Vector3(r.position.x + r.size.x * 0.5, y0 - SLAB * 0.5, r.position.y + r.size.y * 0.5), Vector3(r.size.x, SLAB, r.size.y))
	for r in _floor_rects(f + 1):
		_box(f, "ceiling", Vector3(r.position.x + r.size.x * 0.5, y0 + FH - SLAB - 0.012, r.position.y + r.size.y * 0.5), Vector3(r.size.x, 0.02, r.size.y), false)

	# Outside walls with windows (and the front door on the ground floor).
	var win := [WIN_SILL, WIN_TOP]
	var north := [[1.5, 3.5, win[0], win[1]], [6.5, 8.5, win[0], win[1]], [13.0, 15.0, win[0], win[1]]]
	var south := [[2.0, 4.0, win[0], win[1]], [8.0, 10.0, win[0], win[1]], [14.0, 16.0, win[0], win[1]]]
	var west := [[1.0, 3.0, win[0], win[1]], [9.0, 11.0, win[0], win[1]]]
	if f == 0:
		west.append([4.5, 5.5, 0.0, DOOR_H])
	else:
		west.append([4.4, 5.6, win[0], win[1]])
	var east := [[1.0, 2.6, win[0], win[1]], [4.4, 5.6, win[0], win[1]], [9.0, 11.0, win[0], win[1]]]
	_wall_x(f, 0.0, -EXT_T * 0.5, HX + EXT_T * 0.5, EXT_T, north)
	_wall_x(f, HZ, -EXT_T * 0.5, HX + EXT_T * 0.5, EXT_T, south)
	_wall_z(f, 0.0, 0.0, HZ, EXT_T, west)
	_wall_z(f, HX, 0.0, HZ, EXT_T, east)

	# Inside walls with door holes.
	var arch_a := 10.4
	var arch_b := 11.6
	if f == 1:
		arch_a = 16.6
		arch_b = 17.8
	_wall_x(f, 4.0, 0.0, HX, INT_T, [[2.0, 3.0, 0.0, DOOR_H], [7.0, 8.0, 0.0, DOOR_H], [arch_a, arch_b, 0.0, DOOR_H + 0.2]])
	_wall_x(f, 6.0, 0.0, HX, INT_T, [[2.5, 3.5, 0.0, DOOR_H], [8.5, 9.5, 0.0, DOOR_H], [14.5, 15.5, 0.0, DOOR_H]])
	_wall_z(f, 5.0, 0.0, 4.0, INT_T, [])
	_wall_z(f, 10.0, 0.0, 4.0, INT_T, [])
	_wall_z(f, 6.0, 6.0, HZ, INT_T, [])
	_wall_z(f, 12.0, 6.0, HZ, INT_T, [])


func _build_stairs() -> void:
	# Stair A: ground -> middle floor, climbing towards +X.
	_stair_flight(0, 12.0, 16.5, 0.15, 1.35, 0.0)
	# Stair B: middle -> top floor, climbing towards -X.
	_stair_flight(1, 16.5, 12.0, 1.5, 2.7, FH)
	# Wall between stair B and the hole above stair A.
	_box(1, "wall", Vector3(14.25, FH + FH * 0.5, 1.425), Vector3(4.5, FH, 0.15))
	# Railings so nobody falls into the stair holes.
	_box(1, "wood", Vector3(12.0, FH + 0.5, 0.75), Vector3(0.12, 1.0, 1.2))
	_box(2, "wood", Vector3(14.25, 2 * FH + 0.5, 1.425), Vector3(4.5, 1.0, 0.15))
	_box(2, "wood", Vector3(14.25, 2 * FH + 0.5, 2.775), Vector3(4.5, 1.0, 0.15))
	_box(2, "wood", Vector3(16.575, 2 * FH + 0.5, 2.175), Vector3(0.15, 1.0, 1.35))


func _stair_flight(f: int, x_from: float, x_to: float, z0: float, z1: float, y_base: float) -> void:
	var steps := 15
	var run := absf(x_to - x_from) / steps
	var rise := FH / steps
	var dir := 1.0 if x_to > x_from else -1.0
	var zc := (z0 + z1) * 0.5
	var zw := z1 - z0
	for i in range(steps):
		var top := rise * (i + 1)
		var xc := x_from + dir * run * (i + 0.5)
		_box(f, "floor", Vector3(xc, y_base + top * 0.5, zc), Vector3(run, top, zw), false)
	# A smooth ramp is used for walking, so climbing is easy on a phone.
	var pts := PackedVector3Array([
		Vector3(x_from, y_base, z0), Vector3(x_from, y_base, z1),
		Vector3(x_to, y_base, z0), Vector3(x_to, y_base, z1),
		Vector3(x_to, y_base + FH, z0), Vector3(x_to, y_base + FH, z1)])
	var shape := ConvexPolygonShape3D.new()
	shape.points = pts
	var cs := CollisionShape3D.new()
	cs.shape = shape
	bodies[f].add_child(cs)


func _build_roof_and_ground() -> void:
	_box(2, "wall", Vector3(HX * 0.5, 3.0 * FH - SLAB * 0.5, HZ * 0.5), Vector3(HX + 0.6, SLAB, HZ + 0.6))
	var g := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(90, 90)
	g.mesh = pm
	var gm := Assets.get_material("ground").duplicate() as StandardMaterial3D
	gm.uv1_scale = Vector3(22, 22, 1)
	g.material_override = gm
	g.position = Vector3(HX * 0.5, -0.02, HZ * 0.5)
	g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	exterior_root.add_child(g)
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(90, 0.2, 90)
	cs.shape = shape
	cs.position = Vector3(HX * 0.5, -0.12, HZ * 0.5)
	body.add_child(cs)
	exterior_root.add_child(body)
	# Invisible fence far outside so the player cannot walk away forever.
	for side in [[Vector3(HX * 0.5, 1.5, -12.0), Vector3(60, 3, 0.5)], [Vector3(HX * 0.5, 1.5, HZ + 12.0), Vector3(60, 3, 0.5)],
			[Vector3(-14.0, 1.5, HZ * 0.5), Vector3(0.5, 3, 60)], [Vector3(HX + 12.0, 1.5, HZ * 0.5), Vector3(0.5, 3, 60)]]:
		var fcs := CollisionShape3D.new()
		var fs := BoxShape3D.new()
		fs.size = side[1]
		fcs.shape = fs
		fcs.position = side[0]
		body.add_child(fcs)


func _build_lights_and_probes(f: int) -> void:
	var y0 := f * FH
	var spots := [Vector2(3, 10), Vector2(9, 10), Vector2(15, 10), Vector2(2.5, 2), Vector2(7.5, 2), Vector2(4.5, 5), Vector2(13.5, 5), Vector2(11.0, 2.2)]
	for s in spots:
		var l := OmniLight3D.new()
		l.position = Vector3(s.x, y0 + 2.5, s.y)
		l.light_color = Color(1.0, 0.9, 0.76)
		l.light_energy = 0.85
		l.light_specular = 0.6
		l.omni_range = 5.5
		l.omni_attenuation = 1.3
		l.shadow_enabled = false
		l.light_cull_mask = layer_of(f) | 1
		floor_nodes[f].add_child(l)
		_box(f, "lamp", Vector3(s.x, y0 + FH - SLAB - 0.035, s.y), Vector3(0.42, 0.04, 0.42), false)
	# One reflection probe per room for real PBR reflections.
	var rooms := [Rect2(0, 6, 6, 8), Rect2(6, 6, 6, 8), Rect2(12, 6, 6, 8), Rect2(0, 0, 5, 4), Rect2(5, 0, 5, 4), Rect2(0, 4, 18, 2), Rect2(10, 0, 8, 4)]
	for r in rooms:
		var p := ReflectionProbe.new()
		p.size = Vector3(r.size.x, FH - SLAB, r.size.y)
		p.position = Vector3(r.position.x + r.size.x * 0.5, y0 + (FH - SLAB) * 0.5, r.position.y + r.size.y * 0.5)
		p.box_projection = true
		p.interior = true
		p.enable_shadows = false
		p.update_mode = ReflectionProbe.UPDATE_ONCE
		p.intensity = 1.0
		probes_root.add_child(p)


# ================================================================ doors

func _add_door(f: int, pos: Vector3, rot_y: float, room: String):
	var d = DoorScript.new()
	d.floor_index = f
	d.room_name = room
	floor_nodes[f].add_child(d)
	d.position = pos
	d.rotation.y = rot_y
	d.build(DOOR_W, DOOR_H, layer_of(f))
	doors.append(d)
	return d


func _door_frame(f: int, c: Vector3, along_x: bool, depth: float) -> void:
	var half := DOOR_W * 0.5 + 0.03
	if along_x:
		_box(f, "wood", c + Vector3(-half, DOOR_H * 0.5, 0), Vector3(0.06, DOOR_H, depth), false)
		_box(f, "wood", c + Vector3(half, DOOR_H * 0.5, 0), Vector3(0.06, DOOR_H, depth), false)
		_box(f, "wood", c + Vector3(0, DOOR_H + 0.03, 0), Vector3(DOOR_W + 0.12, 0.06, depth), false)
	else:
		_box(f, "wood", c + Vector3(0, DOOR_H * 0.5, -half), Vector3(depth, DOOR_H, 0.06), false)
		_box(f, "wood", c + Vector3(0, DOOR_H * 0.5, half), Vector3(depth, DOOR_H, 0.06), false)
		_box(f, "wood", c + Vector3(0, DOOR_H + 0.03, 0), Vector3(depth, 0.06, DOOR_W + 0.12), false)


func _build_doors() -> void:
	var specs := [["D", 2.5, 4.0, 0.0], ["E", 7.5, 4.0, 0.0], ["A", 3.0, 6.0, PI], ["B", 9.0, 6.0, PI], ["C", 15.0, 6.0, PI]]
	for f in range(3):
		var y0 := f * FH
		for s in specs:
			var pos := Vector3(s[1], y0, s[2])
			var d = _add_door(f, pos, s[3], s[0])
			_door_frame(f, pos, true, INT_T + 0.04)
			room_doors[str(f) + str(s[0])] = d
	front_door = _add_door(0, Vector3(0.0, 0.0, 5.0), -PI * 0.5, "front")
	_door_frame(0, Vector3(0.0, 0.0, 5.0), false, EXT_T + 0.04)
	front_door.locked = true
	front_door.lock_message = "The front door is locked!"

	start_door = room_doors["2A"]
	start_door.locked = true
	start_door.lock_message = "Aunty locked my door! Maybe there is a spare key in this room..."
	study_door = room_doors["1B"]
	study_door.locked = true
	study_door.lock_message = "There is a big padlock on this door."

	for key in room_doors.keys():
		if key != "2A" and key != "1B" and randf() < 0.5:
			room_doors[key].set_open(true, true)


# ================================================================ furniture + items

func _place(f: int, key: String, x: float, z: float, yaw_deg: float, y: float = 0.0, collide: bool = true) -> Node3D:
	var sz: Vector3 = SIZES.get(key, Vector3.ONE)
	var node: Node3D = Assets.make_model(key, sz, "fit")
	var fitted := sz
	if node == null:
		node = fb.make(key, sz)
	else:
		fitted = node.get_meta("fitted_size", sz)
	floor_nodes[f].add_child(node)
	node.position = Vector3(x, f * FH + y, z)
	node.rotation.y = deg_to_rad(yaw_deg)
	Assets.set_layers_recursive(node, layer_of(f))
	node.set_meta("fitted", fitted)
	node.set_meta("height", fitted.y)
	if collide:
		var body := StaticBody3D.new()
		body.collision_layer = 1
		body.collision_mask = 0
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = Vector3(maxf(fitted.x, 0.05), maxf(fitted.y, 0.05), maxf(fitted.z, 0.05))
		cs.shape = shape
		cs.position = Vector3(0, fitted.y * 0.5, 0)
		body.add_child(cs)
		node.add_child(body)
	return node


func _build_furniture() -> void:
	var tops := {}
	for e in FURNITURE:
		var f: int = e[0]
		var key: String = e[1]
		var y := 0.0
		if e.size() > 5:
			var on := str(e[5])
			if on.begins_with("on:"):
				y = float(tops.get(str(f) + on.substr(3), 0.5))
		var n := _place(f, key, float(e[2]), float(e[3]), float(e[4]), y)
		tops[str(f) + key] = float(n.get_meta("height", 0.5)) + y


func _interact_box(node: Node3D, kind: String, prompt: String):
	var fitted: Vector3 = node.get_meta("fitted", Vector3(0.5, 0.5, 0.5))
	var ib = InteractScript.new()
	ib.kind = kind
	ib.prompt = prompt
	ib.collision_layer = 1 | 8
	ib.collision_mask = 0
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(maxf(fitted.x, 0.3), maxf(fitted.y, 0.3), maxf(fitted.z, 0.3))
	cs.shape = shape
	cs.position = Vector3(0, fitted.y * 0.5, 0)
	ib.add_child(cs)
	node.add_child(ib)
	return ib


func _model_or_standin(key: String, mode: String) -> Node3D:
	var sz: Vector3 = SIZES.get(key, Vector3(0.3, 0.3, 0.3))
	var model: Node3D = Assets.make_model(key, sz, mode)
	if model == null:
		model = fb.make(key, sz)
		model.set_meta("fitted_size", sz)
	return model


func spawn_item(f: int, item_id: String, pos: Vector3, yaw: float = 0.0):
	var key: String = ITEM_MODEL.get(item_id, "key_old")
	var model := _model_or_standin(key, "longest")
	var fitted: Vector3 = model.get_meta("fitted_size", Vector3(0.2, 0.05, 0.2))
	var ib = InteractScript.new()
	ib.kind = "pickup"
	ib.item_id = item_id
	ib.prompt = "Take"
	ib.collision_layer = 8
	ib.collision_mask = 0
	ib.add_child(model)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(maxf(fitted.x, 0.3), maxf(fitted.y, 0.14), maxf(fitted.z, 0.3))
	cs.shape = shape
	cs.position = Vector3(0, shape.size.y * 0.5, 0)
	ib.add_child(cs)
	floor_nodes[f].add_child(ib)
	ib.position = pos
	ib.rotation.y = yaw
	Assets.set_layers_recursive(ib, layer_of(f))
	return ib


func _make_lock(f: int, key: String, pos: Vector3, yaw_deg: float, lock_id: String, needs: String, prompt: String):
	var model := _model_or_standin(key, "longest")
	var fitted: Vector3 = model.get_meta("fitted_size", Vector3(0.15, 0.15, 0.05))
	var ib = InteractScript.new()
	ib.kind = "lock"
	ib.prompt = prompt
	ib.data = {"lock": lock_id, "needs": needs}
	ib.collision_layer = 8
	ib.collision_mask = 0
	ib.add_child(model)
	if key == "padlock":
		# Metal hasp the padlock hangs on.
		var hasp := MeshInstance3D.new()
		var hm := BoxMesh.new()
		hm.size = Vector3(0.24, 0.05, 0.012)
		hasp.mesh = hm
		hasp.material_override = Assets.color_mat(Color(0.5, 0.5, 0.52), 0.35, 1.0)
		hasp.position = Vector3(0, fitted.y * 0.85, -0.03)
		ib.add_child(hasp)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(maxf(fitted.x, 0.32), maxf(fitted.y, 0.32), maxf(fitted.z, 0.2))
	cs.shape = shape
	cs.position = Vector3(0, fitted.y * 0.5, 0)
	ib.add_child(cs)
	floor_nodes[f].add_child(ib)
	ib.position = Vector3(pos.x, f * FH + pos.y, pos.z)
	ib.rotation.y = deg_to_rad(yaw_deg)
	Assets.set_layers_recursive(ib, layer_of(f))
	return ib


func _make_planks(f: int, pos: Vector3):
	var ib = InteractScript.new()
	ib.kind = "lock"
	ib.prompt = "Remove"
	ib.data = {"lock": "front_planks", "needs": "hammer"}
	ib.collision_layer = 8
	ib.collision_mask = 0
	for i in range(2):
		var holder := Node3D.new()
		holder.rotation = Vector3(0, PI * 0.5, 0)
		var tilt := Node3D.new()
		tilt.rotation.z = deg_to_rad(32.0 if i == 0 else -32.0)
		holder.add_child(tilt)
		var model := _model_or_standin("planks", "longest")
		var fitted: Vector3 = model.get_meta("fitted_size", SIZES["planks"])
		tilt.add_child(model)
		model.position = Vector3(0, -fitted.y * 0.5, 0.03 * i)
		ib.add_child(holder)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(0.2, 1.0, 1.1)
	cs.shape = shape
	ib.add_child(cs)
	floor_nodes[f].add_child(ib)
	ib.position = Vector3(pos.x, f * FH + pos.y, pos.z)
	Assets.set_layers_recursive(ib, layer_of(f))
	return ib


func _make_note(f: int, pos: Vector3, text: String):
	var ib = InteractScript.new()
	ib.kind = "note"
	ib.prompt = "Read"
	ib.data = {"text": text}
	ib.collision_layer = 8
	ib.collision_mask = 0
	var paper := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(0.21, 0.297)
	paper.mesh = qm
	paper.rotation.x = -PI * 0.5
	paper.position.y = 0.003
	paper.material_override = Assets.color_mat(Color(0.95, 0.93, 0.85), 0.9)
	ib.add_child(paper)
	var scribble := Label3D.new()
	scribble.text = "safe code?\nRED  BLUE\nGREEN  YELLOW"
	scribble.font = Assets.chalk_font
	scribble.font_size = 40
	scribble.pixel_size = 0.0011
	scribble.modulate = Color(0.15, 0.15, 0.2)
	scribble.outline_size = 0
	scribble.rotation.x = -PI * 0.5
	scribble.position.y = 0.006
	ib.add_child(scribble)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(0.32, 0.08, 0.38)
	cs.shape = shape
	cs.position = Vector3(0, 0.04, 0)
	ib.add_child(cs)
	floor_nodes[f].add_child(ib)
	ib.position = Vector3(pos.x, f * FH + pos.y, pos.z)
	Assets.set_layers_recursive(ib, layer_of(f))
	return ib


func _chalk_digit(f: int, pos: Vector3, yaw: float, digit: int, col: Color) -> void:
	var root := Node3D.new()
	floor_nodes[f].add_child(root)
	root.position = Vector3(pos.x, f * FH + pos.y, pos.z)
	root.rotation.y = yaw
	var l := Label3D.new()
	l.text = str(digit)
	l.font = Assets.chalk_font
	l.font_size = 200
	l.pixel_size = 0.0022
	l.modulate = Color(col.r, col.g, col.b, 0.92)
	l.outline_size = 0
	root.add_child(l)
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.27
	tm.outer_radius = 0.3
	tm.rings = 28
	tm.ring_segments = 4
	ring.mesh = tm
	ring.rotation.x = PI * 0.5
	ring.scale = Vector3(1, 0.2, 1)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(col.r, col.g, col.b, 0.9)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring.material_override = mat
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(ring)
	Assets.set_layers_recursive(root, layer_of(f))


func _build_puzzle(code: Array) -> void:
	# 1) Start room (top floor, A): the nightstand drawer hides the room key.
	var ns := _place(2, "nightstand", 0.4, 12.5, 90, 0.0, false)
	var sb = _interact_box(ns, "search", "Search")
	var ns_top := float(ns.get_meta("height", 0.55))
	sb.data = {"item_id": "room_key", "done": false, "floor": 2,
		"spawn": Vector3(0.42, 2 * FH + ns_top + 0.005, 12.5)}

	# 2) Hammer in the attic storage (top floor, B).
	spawn_item(2, "hammer", Vector3(8.6, 2 * FH, 10.6), 0.6)
	# 3) Bolt cutter in aunty's bedroom (middle floor, A).
	spawn_item(1, "bolt_cutter", Vector3(4.7, FH, 7.6), -0.4)
	# 4) Padlock on the study door (middle floor, B) - break it with the hammer.
	_make_lock(1, "padlock", Vector3(8.5, 1.02, 5.86), 180, "study_padlock", "hammer", "Break")
	# 5) Safe + aunty's note inside the study.
	safe_node = _place(1, "safe", 6.4, 8.5, 90, 0.0, false)
	safe_body = _interact_box(safe_node, "safe", "Open safe")
	var desk := _place(1, "desk", 9.0, 13.57, 180)
	_make_note(1, Vector3(9.0, float(desk.get_meta("height", 0.76)) + 0.004, 13.45), NOTE_TEXT)
	# 6) Chalk numbers of the safe code (red, blue, green, yellow).
	_chalk_digit(2, Vector3(17.865, 1.75, 7.5), -PI * 0.5, int(code[0]), CHALK_COLORS[0])
	_chalk_digit(1, Vector3(4.915, 1.75, 2.4), -PI * 0.5, int(code[1]), CHALK_COLORS[1])
	_chalk_digit(0, Vector3(5.0, 1.75, 13.865), PI, int(code[2]), CHALK_COLORS[2])
	_chalk_digit(0, Vector3(11.915, 1.75, 8.0), -PI * 0.5, int(code[3]), CHALK_COLORS[3])
	# 7) Three locks on the front door.
	front_locks["front_padlock"] = _make_lock(0, "padlock", Vector3(0.22, 1.0, 5.38), 90, "front_padlock", "main_key", "Unlock")
	front_locks["front_chain"] = _make_lock(0, "chain", Vector3(0.2, 1.42, 5.0), 90, "front_chain", "bolt_cutter", "Cut")
	front_locks["front_planks"] = _make_planks(0, Vector3(0.26, 1.05, 5.0))


## Called by the game when the safe code is right.
func open_safe() -> void:
	spawn_item(1, "main_key", Vector3(6.95, FH + 0.01, 8.5), 0.3)
	if safe_node != null and is_instance_valid(safe_node):
		Assets.play_3d("unlock", safe_node.global_position + Vector3(0, 0.5, 0), self, 0.0)


# ================================================================ AI waypoints

func _wp(f: int, x: float, z: float) -> int:
	var id := _next_wp
	_next_wp += 1
	astar.add_point(id, Vector3(x, f * FH + 0.1, z))
	wp_floor[id] = f
	return id


func _link(a: int, b: int) -> void:
	astar.connect_points(a, b, true)


func _build_waypoints() -> void:
	var spines: Array = []
	for f in range(3):
		var xs: Array = [0.8, 2.5, 3.0, 7.5, 9.0, 15.0, 17.2]
		var arch := 11.0 if f != 1 else 17.2
		if not xs.has(arch):
			xs.append(arch)
		xs.sort()
		var spine := {}
		var prev := -1
		for x in xs:
			var id := _wp(f, x, 5.0)
			spine[x] = id
			patrol_points.append(id)
			if prev != -1:
				_link(prev, id)
			prev = id
		spines.append(spine)
		for room in ROOM_DOORS.keys():
			var info: Array = ROOM_DOORS[room]
			var inside := _wp(f, info[1], info[2])
			_link(spine[info[0]], inside)
			var ids: Array = [inside]
			var last := inside
			for p in ROOM_PATROL[f][room]:
				var pid := _wp(f, p.x, p.y)
				_link(last, pid)
				last = pid
				ids.append(pid)
				patrol_points.append(pid)
			var door = room_doors.get(str(f) + str(room))
			if door != null:
				door.waypoint_ids = ids
				if door.locked:
					for id in ids:
						astar.set_point_disabled(id, true)

	# Stairs: ground <-> middle (stair A) and middle <-> top (stair B).
	var a0 := _wp(0, 11.0, 3.2)
	_link(spines[0][11.0], a0)
	var a1 := _wp(0, 11.0, 0.75)
	_link(a0, a1)
	var a2 := _wp(0, 12.1, 0.75)
	_link(a1, a2)
	var b0 := _wp(1, 16.4, 0.75)
	_link(a2, b0)
	var b1 := _wp(1, 17.2, 0.75)
	_link(b0, b1)
	var b2 := _wp(1, 17.2, 2.1)
	_link(b1, b2)
	var b3 := _wp(1, 17.2, 3.2)
	_link(b2, b3)
	_link(b3, spines[1][17.2])
	var b4 := _wp(1, 16.4, 2.1)
	_link(b2, b4)
	var c0 := _wp(2, 12.1, 2.1)
	_link(b4, c0)
	var c1 := _wp(2, 11.0, 2.1)
	_link(c0, c1)
	var c2 := _wp(2, 11.0, 3.2)
	_link(c1, c2)
	_link(c2, spines[2][11.0])


## Re-enables the AI points of a room after its door gets unlocked.
func enable_room_points(door) -> void:
	if door == null:
		return
	for id in door.waypoint_ids:
		astar.set_point_disabled(id, false)


func floor_of_point(id: int) -> int:
	return int(wp_floor.get(id, 0))


# ================================================================ meshes

func _slot_material(slot: String) -> Material:
	if slot == "glass":
		return Assets.glass_mat()
	if slot == "lamp":
		return Assets.lamp_mat()
	return Assets.get_material(slot)


## Merges many boxes into one mesh with world-space UVs (textures line up
## across walls) and tangents for the normal maps.
func _build_mesh(list: Array, tile: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for e in list:
		var bm := BoxMesh.new()
		bm.size = e[1]
		st.append_from(bm, 0, Transform3D(Basis(), e[0]))
	var arrays := st.commit_to_arrays()
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var norms: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var uvs := PackedVector2Array()
	uvs.resize(verts.size())
	var inv := 1.0 / tile
	for i in range(verts.size()):
		var v := verts[i]
		var n := norms[i]
		if absf(n.y) > 0.5:
			uvs[i] = Vector2(v.x, v.z) * inv
		elif absf(n.x) > 0.5:
			uvs[i] = Vector2(v.z, -v.y) * inv
		else:
			uvs[i] = Vector2(v.x, -v.y) * inv
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_TANGENT] = null
	var st2 := SurfaceTool.new()
	st2.create_from_arrays(arrays)
	st2.generate_tangents()
	return st2.commit()


func _commit_batches(f: int) -> void:
	var groups: Dictionary = batches[f]
	for slot in groups.keys():
		var list: Array = groups[slot]
		if list.is_empty():
			continue
		var mi := MeshInstance3D.new()
		mi.name = "Mesh_" + str(slot)
		mi.mesh = _build_mesh(list, float(TILE.get(slot, 2.0)))
		mi.material_override = _slot_material(str(slot))
		mi.layers = layer_of(f)
		# Sun shadows come from the shadow proxy, so hidden floors still block sunlight.
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		floor_nodes[f].add_child(mi)


func _commit_shadow_proxy() -> void:
	if shadow_list.is_empty():
		return
	var mi := MeshInstance3D.new()
	mi.name = "SunShadowProxy"
	mi.mesh = _build_mesh(shadow_list, 3.0)
	mi.material_override = Assets.get_material("wall")
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	add_child(mi)


## Only draw the floor the player is on (and the next one near the stairs).
func set_visible_floors(cur: int, near_stairs: bool) -> void:
	for f in range(3):
		var vis: bool = f == cur or (near_stairs and absi(f - cur) == 1)
		var n: Node3D = floor_nodes[f]
		if n.visible != vis:
			n.visible = vis
