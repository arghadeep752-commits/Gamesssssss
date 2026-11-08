class_name MazeData
extends RefCounted
## The house layout (res://assets/map/layout.json, written by tools/maze.py): cells, doors, items, lights.

var L: Dictionary
var cols: int
var rows: int
var cell: float
var x0: float
var z0: float
var astar := AStar2D.new()
var open_cells: Array = []

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
	var pj: Dictionary = L["pooja"]
	for j in range(rows):
		for i in range(cols):
			var id := j * cols + i
			astar.add_point(id, Vector2(i, j))
			if not in_pooja(i, j):
				open_cells.append(Vector2i(i, j))
	for e in L["edges"]:
		var a := int(e[0])
		var b := int(e[1])
		astar.connect_points(a, b, true)

func in_pooja(i: int, j: int) -> bool:
	var p: Dictionary = L["pooja"]
	return i >= int(p["i0"]) and i < int(p["i0"]) + int(p["w"]) and j >= int(p["j0"]) and j < int(p["j0"]) + int(p["h"])

func cell_center(c: Vector2i) -> Vector3:
	return Vector3(x0 + (c.x + 0.5) * cell, 0.0, z0 + (c.y + 0.5) * cell)

func world_to_cell(p: Vector3) -> Vector2i:
	return Vector2i(clampi(int(floor((p.x - x0) / cell)), 0, cols - 1), clampi(int(floor((p.z - z0) / cell)), 0, rows - 1))

## Cell centres from `from` to `to` (inclusive) along open doorways, as world positions.
func path(from_pos: Vector3, to_pos: Vector3) -> PackedVector3Array:
	var a := world_to_cell(from_pos)
	var b := world_to_cell(to_pos)
	var out := PackedVector3Array()
	var ids := astar.get_id_path(a.y * cols + a.x, b.y * cols + b.x)
	for id in ids:
		out.append(cell_center(Vector2i(id % cols, id / cols)))
	return out
