extends RefCounted
## The Hyper3D Rodin models (converted by tools/godot/convert_models.py): vehicles, weapons, street props,
## shop-houses and the rigged characters, loaded once and copied for every use.

const GEN := "res://gen/models/"

var vehicles := {}      # name -> spec dictionary (Vector3 fields converted)
var weapons := {}
var props := {}
var characters := {}
var buildings: Array[String] = []
var char_names: Array[String] = []
var wheel := {}
var _scenes := {}
var _tinted := {}
var _blob_mesh: QuadMesh
var _blob_mat: ShaderMaterial


func init_models() -> void:
	var o = G.load_json(GEN + "models.json")
	if not o is Dictionary:
		push_warning("models.json missing")
		return
	for name in o.get("vehicles", {}):
		var v: Dictionary = o["vehicles"][name].duplicate(true)
		for k in ["seat", "exit", "box", "motor", "tail_rotor"]:
			if v.has(k):
				v[k] = G.v3(v[k])
		if v.has("rotor"):
			v["rotor_r"] = float(v["rotor"][3]) if v["rotor"].size() > 3 else 5.0
			v["rotor"] = G.v3(v["rotor"])
		var lights: Array = []
		for l in v.get("lights", []):
			lights.append(G.v3(l))
		v["lights"] = lights
		var wh: Array = []
		for w in v.get("wheels", []):
			wh.append({"pos": Vector3(w["x"], w["y"], w["z"]), "r": float(w.get("r", 0.3)), "steer": bool(w.get("steer", false)),
				"drive": bool(w.get("drive", false))})
		v["wheels"] = wh
		v["name"] = name
		vehicles[name] = v
	for name in o.get("weapons", {}):
		var w: Dictionary = o["weapons"][name]
		weapons[name] = {"name": name, "length": float(w.get("length", 0.3)), "muzzle": G.v3(w.get("muzzle"))}
	for name in o.get("props", {}):
		var p: Dictionary = o["props"][name]
		props[name] = {"name": name, "kind": p.get("kind", "prop"), "size": G.v3(p.get("size"))}
		if p.get("kind", "") == "building":
			buildings.append(name)
	for name in o.get("characters", {}):
		characters[name] = o["characters"][name]
		char_names.append(name)
	wheel = o.get("wheel", {}) if o.get("wheel") != null else {}
	G.note("models: %d vehicles, %d weapons, %d characters, %d props" % [vehicles.size(), weapons.size(), char_names.size(), props.size()])


func _scene(path: String) -> PackedScene:
	if _scenes.has(path):
		return _scenes[path]
	var s: PackedScene = load(path) if ResourceLoader.exists(path) else null
	if s == null:
		push_warning("model missing: " + path)
	_scenes[path] = s
	return s


func _inst(path: String) -> Node3D:
	var s := _scene(path)
	return s.instantiate() as Node3D if s else null


static func meshes(n: Node, out: Array = []) -> Array:
	if n is MeshInstance3D:
		out.append(n)
	for c in n.get_children():
		meshes(c, out)
	return out


## Vehicle body; 'tint' paints it (white = the model's own colours).
func vehicle(name: String, tint := Color.WHITE) -> Node3D:
	var n := _inst(GEN + "vehicles/%s.glb" % name)
	if n == null:
		return null
	for mi in meshes(n):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		if tint != Color.WHITE:
			var key := name + tint.to_html()
			if not _tinted.has(key):
				var m: Material = mi.get_active_material(0)
				if m is BaseMaterial3D:
					m = m.duplicate()
					m.albedo_color = tint
					m.roughness = minf(m.roughness, 0.55)
				_tinted[key] = m
			mi.material_override = _tinted[key]
	return n


func wheel_model() -> Node3D:
	return _inst(GEN + "vehicles/wheel.glb")


func weapon(name: String) -> Node3D:
	var n := _inst(GEN + "weapons/%s.glb" % name)
	if n:
		for mi in meshes(n):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return n


func prop(name: String) -> Node3D:
	var n := _inst(GEN + "props/%s.glb" % name)
	if n:
		for mi in meshes(n):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return n


## A rigged character with its AnimationPlayer (clips looped as the converter says).
func character(name: String) -> Node3D:
	var n := _inst(GEN + "chars/%s.glb" % name)
	if n == null:
		return null
	var ap: AnimationPlayer = n.find_child("AnimationPlayer", true, false)
	var info: Dictionary = characters.get(name, {}).get("clips", {})
	if ap:
		for clip in info:
			if ap.has_animation(clip):
				var a := ap.get_animation(clip)
				a.loop_mode = Animation.LOOP_LINEAR if info[clip]["loop"] else Animation.LOOP_NONE
	for mi in meshes(n):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return n


## The soft dark patch under people and vehicles.
func blob(parent: Node3D, width: float, length: float, strength := 0.55) -> MeshInstance3D:
	if _blob_mesh == null:
		_blob_mesh = QuadMesh.new()
		_blob_mesh.size = Vector2(1, 1)
		_blob_mesh.orientation = PlaneMesh.FACE_Y
		_blob_mat = ShaderMaterial.new()
		_blob_mat.shader = load("res://shaders/blob.gdshader")
		if ResourceLoader.exists("res://gen/ui/blob.png"):
			_blob_mat.set_shader_parameter("tex", load("res://gen/ui/blob.png"))
		_blob_mat.set_shader_parameter("strength", strength)
	var mi := MeshInstance3D.new()
	mi.mesh = _blob_mesh
	mi.material_override = _blob_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.position = Vector3(0, 0.04, 0)
	mi.scale = Vector3(width, 1, length)
	parent.add_child(mi)
	return mi
