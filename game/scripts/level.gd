class_name Level
extends Node3D
## The school: loads the Blender-built model, dresses it with photo textures and baked lightmaps, builds collisions,
## doors, items, hiding places and the walk grid Ragini uses.

signal noise(pos: Vector3, radius: float)
signal escaped

const MODEL_DIR := "res://assets/models/"
const LM_GAIN := 4.0          # multiplied by the bake's own scale below

var meta := {}
var model: Node3D
var nodes := {}                # name -> Node3D for every mesh in the model
var doors := {}                # name -> door dict
var items := {}                # id -> item dict
var hides: Array = []
var planks: Array = []
var planks_left := 0
var main_unlocked := false
var padlock_nodes: Array = []
var rotors: Array = []
var astar := AStarGrid2D.new()
var grid_origin := Vector2.ZERO
var grid_cell := 0.4
var room_light := {}
var audio = null
var rng := RandomNumberGenerator.new()


func build() -> bool:
	rng.randomize()
	var f := FileAccess.open(MODEL_DIR + "school_meta.json", FileAccess.READ)
	if f == null:
		push_error("school_meta.json missing")
		return false
	meta = JSON.parse_string(f.get_as_text())
	Mats.setup(meta)
	var ps = load(MODEL_DIR + "school.glb")
	if ps == null:
		push_error("school.glb missing")
		return false
	model = ps.instantiate()
	add_child(model)
	_collect(model)
	var gain: float = float(meta.get("lm_scale", 4.0)) * 0.62
	var lms: Dictionary = meta.get("lightmaps", {})
	for r in meta["rooms"]:
		var e = lms.get("arch_" + r["name"], null)
		room_light[r["name"]] = clampf(float(e["mean"]) * 3.2 if e != null else 0.1, 0.05, 0.6)
	for nm in nodes:
		var mi: MeshInstance3D = nodes[nm]
		var lm_tex: Texture2D = null
		if lms.has(nm):
			var p: String = MODEL_DIR + String(lms[nm]["file"])
			if ResourceLoader.exists(p):
				lm_tex = load(p)
		var fl := 0.16
		if lm_tex == null:
			fl = _light_at(mi.global_position)
		if nm == "arch_roof":
			fl = 0.03
		for s in mi.mesh.get_surface_count():
			var m0 := mi.mesh.surface_get_material(s)
			var mname := String(m0.resource_name) if m0 != null else "plaster"
			mi.set_surface_override_material(s, Mats.make(mname, lm_tex, Color(fl, fl, fl * 1.05), gain))
	_build_colliders()
	_build_doors()
	_build_items()
	_build_hides()
	_build_grid()
	_build_lights()
	for d in meta["dynamic"]:
		if d.get("part", "") == "rotor" and nodes.has(d["name"]):
			rotors.append(nodes[d["name"]])
		if d.get("part", "") == "leaves" and nodes.has(d["name"]):
			pass
	return true


func _collect(n: Node) -> void:
	if n is MeshInstance3D:
		nodes[String(n.name)] = n
	for c in n.get_children():
		_collect(c)


func _light_at(p: Vector3) -> float:
	var best := 0.12
	for r in meta["rooms"]:
		var rc = r["rect"]
		if p.x >= rc[0] and p.x <= rc[2] and -p.z >= rc[1] and -p.z <= rc[3]:
			return room_light.get(r["name"], best)
	return best


func v3(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


# ---------------------------------------------------------------------------------------------- collisions
func _build_colliders() -> void:
	var body := StaticBody3D.new()
	body.name = "Walls"
	body.collision_layer = 1
	add_child(body)
	var fl := CollisionShape3D.new()
	var fb := BoxShape3D.new()
	fb.size = Vector3(120, 1, 120)
	fl.shape = fb
	fl.position = Vector3(0, -0.5, 0)
	body.add_child(fl)
	for c in meta["colliders"]:
		var cs := CollisionShape3D.new()
		var b := BoxShape3D.new()
		b.size = Vector3(c[3], c[4], c[5])
		cs.shape = b
		cs.position = Vector3(c[0], c[1], c[2])
		cs.rotation.y = c[6]
		body.add_child(cs)


# ---------------------------------------------------------------------------------------------- doors
func _build_doors() -> void:
	for d in meta["doors"]:
		if d["kind"] == "arch":
			continue
		var door := {"name": d["name"], "pos": v3(d["pos"]) + Vector3(0, 1.15, 0), "open": false, "lock": d["lock"], "leaves": [],
			"t": 0.0, "target": 0.0, "kind": d["kind"], "w": float(d["w"]), "o": d["o"], "room": d["room"], "auto_close": 0.0}
		var body := StaticBody3D.new()
		body.collision_layer = 1
		var cs := CollisionShape3D.new()
		var b := BoxShape3D.new()
		b.size = Vector3(d["w"], d["h"], 0.12) if d["o"] == "h" else Vector3(0.12, d["h"], d["w"])
		cs.shape = b
		body.position = v3(d["pos"]) + Vector3(0, float(d["h"]) / 2.0, 0)
		body.add_child(cs)
		add_child(body)
		door["shape"] = cs
		doors[d["name"]] = door
	for dy in meta["dynamic"]:
		if dy.has("door") and nodes.has(dy["name"]) and doors.has(dy["door"]):
			var into = dy["into"]
			var leaf := int(dy["leaf"])
			var deg := 0.0
			if dy["o"] == "h":
				deg = 96.0 * float(into[1]) * (1.0 if leaf == 0 else -1.0)
			else:
				deg = -96.0 * float(into[0]) * (1.0 if leaf == 0 else -1.0)
			doors[dy["door"]]["leaves"].append([nodes[dy["name"]], deg_to_rad(deg)])
		elif dy.has("plank") and nodes.has(dy["name"]):
			planks.append({"node": nodes[dy["name"]], "pos": v3(dy["pivot"]), "gone": false, "hits": 0})
		elif dy.has("lock") and nodes.has(dy["name"]):
			padlock_nodes.append(nodes[dy["name"]])
	planks_left = planks.size()


func door_label(d: Dictionary) -> String:
	if d["lock"] == "main":
		return ""
	if d["lock"] != null and d["lock"] != "":
		return "Locked"
	return "Close" if d["open"] else "Open"


func toggle_door(d: Dictionary, by_ragini := false) -> void:
	if d["lock"] != null and d["lock"] != "" and not by_ragini:
		return
	d["open"] = not d["open"]
	d["target"] = 1.0 if d["open"] else 0.0
	d["shape"].disabled = d["open"]
	if audio:
		audio.play3d("door_open" if d["open"] else "door_close", d["pos"], -4.0)
	if not by_ragini:
		noise.emit(d["pos"], 7.0)
	d["auto_close"] = 0.0


func open_main() -> void:
	var d: Dictionary = doors["door_main"]
	d["lock"] = null
	d["open"] = true
	d["target"] = 1.0
	d["shape"].disabled = true
	if audio:
		audio.play3d("door_open", d["pos"], 0.0)


func _process(dt: float) -> void:
	for k in doors:
		var d: Dictionary = doors[k]
		if d["t"] != d["target"]:
			d["t"] = move_toward(d["t"], d["target"], dt * 1.8)
			var e: float = smoothstep(0.0, 1.0, d["t"])
			for lf in d["leaves"]:
				lf[0].rotation.y = lf[1] * e
	for r in rotors:
		r.rotate_y(dt * 2.2)


# ---------------------------------------------------------------------------------------------- items
func _build_items() -> void:
	var names := {"hammer": "item_hammer", "main_key": "item_main_key", "office_key": "item_office_key", "store_key": "item_store_key"}
	for id in meta["items"]:
		var it = meta["items"][id]
		if not nodes.has(names[id]):
			continue
		var n: MeshInstance3D = nodes[names[id]]
		var spots: Array = it["spots"]
		var sp = spots[rng.randi_range(0, spots.size() - 1)]
		n.position = v3(sp["pos"]) + Vector3(0, 0.02, 0)
		n.rotation = Vector3(0, rng.randf_range(0, TAU), 0)
		items[id] = {"id": id, "label": String(it["label"]).capitalize(), "node": n, "held": false, "home": n.position}
		_relight(n)


func _relight(n: MeshInstance3D, v := -1.0) -> void:
	var l := v if v >= 0.0 else maxf(_light_at(n.global_position), 0.16) * 1.5
	for s in n.mesh.get_surface_count():
		var m = n.get_surface_override_material(s)
		if m is ShaderMaterial:
			m.set_shader_parameter("flat_light", Vector3(l, l, l))


func _build_hides() -> void:
	var furn: Array = meta["furniture"]
	var count := 0
	for i in furn.size():
		var f = furn[i]
		if f["kind"] != "almirah":
			continue
		var a := deg_to_rad(float(f["yaw"]))
		var front := Vector3(sin(a), 0, cos(a))
		var h := {"pos": v3(f["pos"]), "front": front, "doors": [], "t": 0.0, "target": 0.0}
		for dy in meta["dynamic"]:
			if dy.get("kind", "") == "almirah" and int(dy.get("furn", -1)) == i and nodes.has(dy["name"]):
				var sgn := -1.0 if dy["part"] == "door_L" else 1.0
				h["doors"].append([nodes[dy["name"]], sgn])
		hides.append(h)
		count += 1


func set_hide_doors(h: Dictionary, amount: float) -> void:
	for d in h["doors"]:
		d[0].rotation.y = d[1] * amount


# ---------------------------------------------------------------------------------------------- the walk grid
func _build_grid() -> void:
	var g = meta["grid"]
	grid_cell = float(g["cell"])
	grid_origin = Vector2(float(g["x0"]), float(g["y0"]))
	astar.region = Rect2i(0, 0, int(g["nx"]), int(g["ny"]))
	astar.cell_size = Vector2(1, 1)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.update()
	var rows: Array = g["rows"]
	for j in rows.size():
		var row: String = rows[j]
		for i in row.length():
			if row[i] == "#":
				astar.set_point_solid(Vector2i(i, j), true)


func cell_of(p: Vector3) -> Vector2i:
	# Godot z = -Blender y
	var c := Vector2i(int(floor((p.x - grid_origin.x) / grid_cell)), int(floor((-p.z - grid_origin.y) / grid_cell)))
	return c.clamp(Vector2i.ZERO, astar.region.size - Vector2i.ONE)


func cell_pos(c: Vector2i) -> Vector3:
	return Vector3(grid_origin.x + (c.x + 0.5) * grid_cell, 0, -(grid_origin.y + (c.y + 0.5) * grid_cell))


func nearest_free(c: Vector2i) -> Vector2i:
	if not astar.is_point_solid(c):
		return c
	for r in range(1, 8):
		for dx in range(-r, r + 1):
			for dy in range(-r, r + 1):
				var q := c + Vector2i(dx, dy)
				if astar.region.has_point(q) and not astar.is_point_solid(q):
					return q
	return c


func find_path(from: Vector3, to: Vector3) -> Array:
	var a := nearest_free(cell_of(from))
	var b := nearest_free(cell_of(to))
	var out: Array = []
	for c in astar.get_id_path(a, b):
		out.append(cell_pos(c))
	return out


func _build_lights() -> void:
	# real lights only matter for Ragini and other lit meshes; the school itself uses its baked lightmaps
	for lt in meta["lights"]:
		if lt["kind"] == "dead":
			continue
		var o := OmniLight3D.new()
		o.position = v3(lt["pos"]) - Vector3(0, 0.35, 0)
		o.omni_range = 7.5
		o.light_energy = 1.1
		o.light_color = Color(0.85, 0.92, 1.0) if lt["kind"] == "tube" else Color(1.0, 0.75, 0.5)
		o.shadow_enabled = false
		add_child(o)


# ---------------------------------------------------------------------------------------------- what the player is looking at
func target(cam_pos: Vector3, fwd: Vector3, held: String) -> Dictionary:
	var best := {}
	var best_score := 0.0
	var cands: Array = []
	for id in items:
		var it: Dictionary = items[id]
		if not it["held"]:
			cands.append({"kind": "item", "pos": it["node"].global_position, "label": it["label"], "ref": it, "r": 2.3})
	for k in doors:
		var d: Dictionary = doors[k]
		if d["lock"] == "main":
			continue
		var lab := door_label(d)
		if lab == "Locked":
			lab = "Locked"
		cands.append({"kind": "door", "pos": d["pos"], "label": lab, "ref": d, "r": 2.4})
	for h in hides:
		cands.append({"kind": "hide", "pos": h["pos"] + Vector3(0, 1.1, 0), "label": "Hide", "ref": h, "r": 2.0})
	if doors.has("door_main") and doors["door_main"]["lock"] == "main":
		for p in planks:
			if not p["gone"]:
				cands.append({"kind": "plank", "pos": p["pos"], "label": "Planks", "ref": p, "r": 2.3})
		if planks_left == 0:
			cands.append({"kind": "padlock", "pos": doors["door_main"]["pos"], "label": "Main Door Lock", "ref": null, "r": 2.3})
		elif true:
			cands.append({"kind": "maindoor", "pos": doors["door_main"]["pos"] + Vector3(0, -0.5, 0), "label": "Main Door", "ref": null, "r": 2.0})
	for c in cands:
		var to: Vector3 = c["pos"] - cam_pos
		var dist := to.length()
		if dist > c["r"] or dist < 0.05:
			continue
		var dot := fwd.dot(to / dist)
		var need := 0.9 if c["kind"] != "door" else 0.8
		if dot < need:
			continue
		var score := dot - dist * 0.03 + (0.03 if c["kind"] == "item" else 0.0) + (0.02 if c["kind"] == "plank" else 0.0)
		if score > best_score:
			best_score = score
			best = c
	return best
