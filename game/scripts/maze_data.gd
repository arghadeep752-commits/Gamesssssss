class_name MazeData
extends RefCounted
## The house layout (res://assets/map/layout.json, written by tools/house.py): rooms on two floors and the walking
## graph Chaya follows - one point per walkable cell (x, floor height, z), linked through open sides, doorways and the
## stairs. Cells are Vector3i(i, j, floor).

var L: Dictionary
var cols: int
var rows: int
var cell: float
var x0: float
var z0: float
var floor_h := 3.3
var astar := AStar3D.new()
var open_cells: Array = []
var _ids := {}
var _cells := {}

static func load_layout() -> MazeData:
	var f := FileAccess.open("res://assets/map/layout.json", FileAccess.READ)
	if f == null:
		push_error("layout.json missing")
		return null
	var m := MazeData.new()
	m.L = JSON.parse_string(f.get_as_text())
	m._init_graph()
	return m

func _init_graph() -> void:
	cols = int(L["cols"])
	rows = int(L["rows"])
	cell = float(L["cell"])
	x0 = float(L["x0"])
	z0 = float(L["z0"])
	floor_h = float(L.get("floor_h", 3.3))
	for n in L["nodes"]:
		var c := Vector3i(int(n[0]), int(n[1]), int(n[2]))
		var id := c.z * cols * rows + c.y * cols + c.x
		astar.add_point(id, cell_center(c))
		open_cells.append(c)
		_ids[c] = id
		_cells[id] = c
	for l in L["links"]:
		var a := Vector3i(int(l[0][0]), int(l[0][1]), int(l[0][2]))
		var b := Vector3i(int(l[1][0]), int(l[1][1]), int(l[1][2]))
		if _ids.has(a) and _ids.has(b):
			astar.connect_points(_ids[a], _ids[b], true)

func cell_center(c: Vector3i) -> Vector3:
	return Vector3(x0 + (c.x + 0.5) * cell, c.z * floor_h, z0 + (c.y + 0.5) * cell)

func floor_of(y: float) -> int:
	return 1 if y > floor_h * 0.55 else 0

## The walkable cell under a position (the nearest one when standing on the stairs or by a railing).
func world_to_cell(p: Vector3) -> Vector3i:
	var c := Vector3i(clampi(int(floor((p.x - x0) / cell)), 0, cols - 1), clampi(int(floor((p.z - z0) / cell)), 0, rows - 1), floor_of(p.y))
	if _ids.has(c):
		return c
	var id := astar.get_closest_point(p)
	return _cells.get(id, open_cells[0])

func cell_dist(a: Vector3i, b: Vector3i) -> int:
	return absi(a.x - b.x) + absi(a.y - b.y) + absi(a.z - b.z) * 4

## Cell centres from `from` to `to` (inclusive) through open sides, doorways and the stairs, as world positions.
func path(from_pos: Vector3, to_pos: Vector3) -> PackedVector3Array:
	var a := world_to_cell(from_pos)
	var b := world_to_cell(to_pos)
	var out := PackedVector3Array()
	for id in astar.get_id_path(_ids[a], _ids[b]):
		out.append(cell_center(_cells[id]))
	return out
