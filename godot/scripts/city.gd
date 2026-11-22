extends Node3D
## Agartala: streams the 128 m map chunks built by tools/city (render meshes, collision mesh, building boxes, the
## Hyper3D shop-houses and street props standing in them), the sea, the countryside and the far hills, the water
## levels and the street lamps.

const GEN := "res://gen/city/"

var half := 650.0
var chunk_size := 128.0
var render_dist := 430.0
var coll_dist := 170.0
var meta: Dictionary = {}
var points: Array = []          # {kind, name, label, model, p, yaw, parked, owned}
var zones: Array = []           # {name, c: Vector2, r}
var lamps: PackedVector3Array = []
var loaded_chunks := 0

var mats := {}                   # group id -> ShaderMaterial
var sea_mat: ShaderMaterial
var chunks: Array = []           # Chunk dictionaries
var by_key := {}
var boxes_by_chunk := {}        # key -> Array of [Vector3 centre, Vector3 size, yaw]
var water: PackedByteArray
var wn := 0
var wcell := 4.0
var sea_level := -1.0
var cursor := 0
var lamp_lights: Array[OmniLight3D] = []


func key(ix: int, iz: int) -> int:
	return ix * 4096 + iz


## Chunk indices are the generator's (x east, z north): Godot's z is mirrored, so convert before looking up.
func ixz(p: Vector3) -> Vector2i:
	var n := int(ceil(2.0 * half / chunk_size))
	var ix := clampi(int(floor((p.x + half) / chunk_size)), 0, n - 1)
	var iz := clampi(int(floor((-p.z + half) / chunk_size)), 0, n - 1)
	return Vector2i(ix, iz)


func init_city() -> void:
	G.city = self
	var m = G.load_json(GEN + "meta.json")
	meta = m if m is Dictionary else {}
	half = float(meta.get("half", 650.0))
	chunk_size = float(meta.get("chunk", 128.0))
	read_meta()
	make_materials()
	read_directory()
	bucket_objects()
	load_extras()
	load_colliders()
	load_water()
	build_lamp_glows()
	G.note("city: %d chunks, %d lamps, %d points" % [chunks.size(), lamps.size(), points.size()])


func read_meta() -> void:
	for l in meta.get("lamps", []):
		lamps.append(G.v3(l))
	for o in meta.get("points", []):
		points.append({"kind": o.get("kind", ""), "name": o.get("name", ""), "label": o.get("label", o.get("name", "")),
			"model": o.get("model", ""), "p": G.v3(o.get("p")), "yaw": float(o.get("yaw", 0.0)),
			"parked": bool(o.get("parked", false)), "owned": bool(o.get("owned", false))})
	for o in meta.get("landmarks", []):
		points.append({"kind": "landmark", "name": o.get("name", ""), "label": o.get("label", o.get("name", "")), "model": "",
			"p": G.v3(o.get("p")), "yaw": float(o.get("yaw", 0.0)), "parked": false, "owned": false})
	for o in meta.get("zones", []):
		var c: Array = o.get("c", [0, 0])
		zones.append({"name": o.get("name", ""), "c": Vector2(c[0], c[1]), "r": float(o.get("r", 100.0))})
	sea_level = float(meta.get("sea_level", -1.0))


func point(kind: String) -> Dictionary:
	for p in points:
		if p["kind"] == kind:
			return p
	return {}


func zone_at(p: Vector3) -> String:
	var best := ""
	var bd := 1e9
	for z in zones:
		var d := Vector2(p.x, p.z).distance_to(z["c"])
		if d < z["r"] and d / z["r"] < bd:
			bd = d / z["r"]
			best = z["name"]
	return best if best != "" else "Agartala"


func make_materials() -> void:
	var albedo: TextureLayered = load(GEN + "layers.png") if ResourceLoader.exists(GEN + "layers.png") else null
	var normals: TextureLayered = load(GEN + "layers_n.png") if ResourceLoader.exists(GEN + "layers_n.png") else null
	var names := {0: "world", 1: "foliage", 2: "water", 3: "terrain"}
	for id in names:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/%s.gdshader" % names[id])
		if albedo:
			m.set_shader_parameter("layers", albedo)
		if normals and id == 0:
			m.set_shader_parameter("layers_n", normals)
		mats[id] = m
		G.env.register(m)
	sea_mat = mats[2].duplicate()
	sea_mat.set_shader_parameter("waves", 2.2)
	sea_mat.set_shader_parameter("deep", Color(0.03, 0.13, 0.20))
	sea_mat.set_shader_parameter("shallow", Color(0.10, 0.30, 0.32))
	G.env.register(sea_mat)


func set_normal_maps(on: bool) -> void:
	mats[0].set_shader_parameter("normal_maps", on)


func read_directory() -> void:
	var idx = G.load_json(GEN + "chunks.json")
	if not idx is Dictionary:
		push_warning("city chunks missing")
		return
	chunk_size = float(idx.get("size", 128.0))
	for k in idx["chunks"]:
		var c := {"ix": int(k[0]), "iz": int(k[1]), "node": null, "coll": null, "r": false, "c": false,
			"objects": [], "object_nodes": []}
		c["centre"] = Vector3((c["ix"] + 0.5) * chunk_size - half, 0.0, -((c["iz"] + 0.5) * chunk_size - half))
		chunks.append(c)
		by_key[key(c["ix"], c["iz"])] = c


func _chunk_data(c: Dictionary) -> Array:
	var b := FileAccess.get_file_as_bytes(GEN + "chunks/%d_%d.bin" % [c["ix"], c["iz"]])
	if b.is_empty():
		return []
	var v = bytes_to_var(b)
	return v if v is Array else []


func chunk_of(p: Vector3) -> Dictionary:
	var k := ixz(p)
	return by_key.get(key(k.x, k.y), {})


func make_mesh(arrays: Array) -> ArrayMesh:
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return m


func load_chunk(c: Dictionary, data: Array) -> void:
	var node := Node3D.new()
	node.name = "chunk_%d_%d" % [c["ix"], c["iz"]]
	add_child(node)
	for s in data:
		var gid: int = s[0]
		if gid == 4:
			continue
		var mi := MeshInstance3D.new()
		mi.mesh = make_mesh(s[1])
		mi.material_override = mats[clamp(gid, 0, 3)]
		# buildings and trees throw sun shadows; the ground and the water only receive them
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if gid <= 1 else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(mi)
	c["node"] = node
	loaded_chunks += 1
	load_objects(c)


func unload_chunk(c: Dictionary) -> void:
	unload_objects(c)
	if c["node"]:
		c["node"].queue_free()
	c["node"] = null
	loaded_chunks -= 1


func load_coll(c: Dictionary, data: Array) -> void:
	var body := StaticBody3D.new()
	body.name = "coll_%d_%d" % [c["ix"], c["iz"]]
	body.collision_layer = G.L_WORLD
	body.collision_mask = 0
	for s in data:
		if s[0] != 4:
			continue
		var shape := ConcavePolygonShape3D.new()
		shape.set_faces(s[1])
		shape.backface_collision = true
		var cs := CollisionShape3D.new()
		cs.shape = shape
		body.add_child(cs)
	for b in boxes_by_chunk.get(key(c["ix"], c["iz"]), []):
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = b[1]
		cs.shape = bs
		cs.transform = Transform3D(Basis(Vector3.UP, deg_to_rad(b[2])), b[0])
		body.add_child(cs)
	add_child(body)
	c["coll"] = body


func unload_coll(c: Dictionary) -> void:
	if c["coll"]:
		c["coll"].queue_free()
	c["coll"] = null


## Loads the chunks near 'focus' (a few per call) and drops the far ones.
func stream(focus: Vector3, budget: int) -> void:
	var n := chunks.size()
	if n == 0:
		return
	var r2 := render_dist + chunk_size * 0.71
	var c2 := coll_dist + chunk_size * 0.71
	for k in n:
		if budget <= 0:
			break
		cursor = (cursor + 1) % n
		var c: Dictionary = chunks[cursor]
		var d := Vector2(c["centre"].x, c["centre"].z).distance_to(Vector2(focus.x, focus.z))
		var want_r := d < r2
		var want_c := d < c2
		var data: Array = []
		if (want_r and not c["r"]) or (want_c and not c["c"]):
			data = _chunk_data(c)
		if want_r and not c["r"]:
			load_chunk(c, data)
			c["r"] = true
			budget -= 1
		elif not want_r and d > r2 + 60.0 and c["r"]:
			unload_chunk(c)
			c["r"] = false
		if want_c and not c["c"]:
			load_coll(c, data)
			c["c"] = true
			budget -= 1
		elif not want_c and d > c2 + 40.0 and c["c"]:
			unload_coll(c)
			c["c"] = false


func stream_now(focus: Vector3) -> void:
	for i in 3:
		stream(focus, 100000)


func collision_ready(p: Vector3) -> bool:
	var c := chunk_of(p)
	return c.is_empty() or c["c"]


# ------------------------------------------------------------------------------------------------ props
func bucket_objects() -> void:
	var n := 0
	for o in meta.get("objects", []):
		var c := chunk_of(G.v3(o["p"]))
		if not c.is_empty():
			c["objects"].append(o)
			n += 1
	G.note("city objects: %d" % n)


func load_objects(c: Dictionary) -> void:
	var M = G.game.models if G.game else null
	if M == null:
		return
	for o in c["objects"]:
		var p := G.v3(o["p"])
		var model: String = o.get("m", "")
		var scale := 1.0
		if o.has("slot"):
			# one of the shop-houses that fits the lot (the same one every time for this spot)
			if M.buildings.is_empty():
				continue
			var w := float(o.get("w", 8.0))
			var d := float(o.get("d", 10.0))
			var h := absi(int(p.x * 73.1 - p.z * 19.7))
			model = ""
			for k in M.buildings.size():
				var cand: String = M.buildings[(h + k) % M.buildings.size()]
				var size: Vector3 = M.props[cand]["size"]
				var s := minf(w / maxf(0.5, size.x), d / maxf(0.5, size.z))
				if s > 0.7:
					model = cand
					scale = minf(1.25, s)
					break
			if model == "":
				continue
		if model == "" or not M.props.has(model):
			continue
		var node: Node3D = M.prop(model)
		if node == null:
			continue
		add_child(node)
		node.transform = Transform3D(Basis(Vector3.UP, deg_to_rad(float(o.get("yaw", 0.0)))).scaled(Vector3.ONE * scale), p)
		if model != "water_tank":
			var size: Vector3 = M.props[model]["size"]
			var body := StaticBody3D.new()
			body.collision_layer = G.L_WORLD
			body.collision_mask = 0
			var cs := CollisionShape3D.new()
			var bs := BoxShape3D.new()
			bs.size = Vector3(size.x * 0.92, size.y, size.z * 0.92)
			cs.shape = bs
			cs.position = Vector3(0, size.y * 0.5, 0)
			body.add_child(cs)
			node.add_child(body)
		c["object_nodes"].append(node)


func unload_objects(c: Dictionary) -> void:
	for n in c["object_nodes"]:
		if is_instance_valid(n):
			n.queue_free()
	c["object_nodes"] = []


# ------------------------------------------------------------------------------------------------ extras
func load_extras() -> void:
	var f := FileAccess.open(GEN + "extras.bin", FileAccess.READ)
	if f == null:
		return
	var d = bytes_to_var(f.get_buffer(f.get_length()))
	if not d is Dictionary:
		return
	for name in d:
		var mi := MeshInstance3D.new()
		mi.name = "extra_" + name
		mi.mesh = make_mesh(d[name])
		mi.material_override = sea_mat if name == "sea" else (mats[3] if name == "skirt" else mats[0])
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)


func load_colliders() -> void:
	var f := FileAccess.open(GEN + "colliders.bin", FileAccess.READ)
	if f == null:
		return
	var a = bytes_to_var(f.get_buffer(f.get_length()))
	if not a is PackedFloat32Array:
		return
	var n: int = a.size() / 7
	for i in n:
		var cx: float = a[i * 7]
		var cy: float = a[i * 7 + 1]
		var cz: float = a[i * 7 + 2]
		var size := Vector3(maxf(0.05, a[i * 7 + 3]), maxf(0.05, a[i * 7 + 4]), maxf(0.05, a[i * 7 + 5]))
		var kk := ixz(Vector3(cx, 0, cz))
		var k := key(kk.x, kk.y)
		if not boxes_by_chunk.has(k):
			boxes_by_chunk[k] = []
		boxes_by_chunk[k].append([Vector3(cx, cy + size.y * 0.5, cz), size, a[i * 7 + 6]])


func load_water() -> void:
	var f := FileAccess.open(GEN + "water.bin", FileAccess.READ)
	if f == null:
		return
	var d = bytes_to_var(f.get_buffer(f.get_length()))
	if d is Dictionary:
		wn = d["n"]
		wcell = d["cell"]
		water = d["levels"]


## Water surface height at (x, z), or NAN on dry land.
func water_level(x: float, z: float) -> float:
	if wn == 0:
		return NAN
	var i := int(floor((x + half) / wcell))
	var j := int(floor((z + half) / wcell))
	if i < 0 or j < 0 or i >= wn or j >= wn:
		return sea_level                 # the open sea past the map
	var v := water.decode_s16((j * wn + i) * 2)
	return NAN if v == -32768 else v / 100.0


func ground(p: Vector3, fallback := 0.0) -> float:
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(p + Vector3(0, 30, 0), p + Vector3(0, -50, 0), G.L_WORLD)
	var hit := space.intersect_ray(q)
	return hit["position"].y if hit else fallback


# ------------------------------------------------------------------------------------------------ lamps
func build_lamp_glows() -> void:
	if lamps.is_empty():
		return
	var n := lamps.size()
	var P := PackedVector3Array()
	var U := PackedVector2Array()
	var U2 := PackedVector2Array()
	var C := PackedColorArray()
	var I := PackedInt32Array()
	var corners := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
	for i in n:
		for k in 4:
			P.append(lamps[i])
			U.append(corners[k])
			U2.append(Vector2(1.6, 0))
			C.append(Color(1.0, 0.84, 0.59, 0.9))
		I.append_array([i * 4, i * 4 + 1, i * 4 + 2, i * 4, i * 4 + 2, i * 4 + 3])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = P
	arr[Mesh.ARRAY_TEX_UV] = U
	arr[Mesh.ARRAY_TEX_UV2] = U2
	arr[Mesh.ARRAY_COLOR] = C
	arr[Mesh.ARRAY_INDEX] = I
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance3D.new()
	mi.name = "lamp_glows"
	mi.mesh = m
	mi.custom_aabb = AABB(Vector3(-half, -50, -half), Vector3(half * 2, 200, half * 2))
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/glow.gdshader")
	if ResourceLoader.exists("res://gen/ui/glow.png"):
		mat.set_shader_parameter("tex", load("res://gen/ui/glow.png"))
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	G.env.register(mat)
	add_child(mi)
	# a few real lights follow the camera from lamp to lamp at night (pools of light on the road)
	for i in 6:
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.78, 0.5)
		l.omni_range = 16.0
		l.omni_attenuation = 1.2
		l.light_energy = 0.0
		l.shadow_enabled = false
		l.visible = false
		add_child(l)
		lamp_lights.append(l)


func update_lamp_lights(focus: Vector3, night: float) -> void:
	if lamp_lights.is_empty():
		return
	var on := night > 0.35
	if not on:
		for l in lamp_lights:
			l.visible = false
		return
	var best: Array = []
	for p in lamps:
		var d := p.distance_squared_to(focus)
		if d < 90.0 * 90.0:
			best.append([d, p])
	best.sort_custom(func(a, b): return a[0] < b[0])
	for i in lamp_lights.size():
		var l := lamp_lights[i]
		if i < best.size():
			l.visible = true
			l.global_position = best[i][1] + Vector3(0, -0.4, 0)
			l.light_energy = 2.2 * clampf((night - 0.35) * 3.0, 0.0, 1.0)
		else:
			l.visible = false
