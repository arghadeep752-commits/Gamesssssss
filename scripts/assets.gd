extends Node
## Loads the real assets that the GitHub build downloads:
##  - chalk font (dafont)          -> res://assets/fonts/chalk.ttf
##  - photo PBR textures (CC0)     -> res://assets/textures/textures.json
##  - real recorded sounds (CC0)   -> res://assets/sounds/sounds.json
##  - Sketchfab 3D models          -> res://assets/models/models.json
## If something is missing, the game still works with simple fallbacks.

const TEX_JSON := "res://assets/textures/textures.json"
const SND_JSON := "res://assets/sounds/sounds.json"
const MDL_JSON := "res://assets/models/models.json"
const CREDITS_TXT := "res://assets/credits.txt"
const FONT_CANDIDATES := ["res://assets/fonts/chalk.ttf", "res://assets/fonts/chalk.otf"]

const FALLBACK_COLORS := {
	"wall": Color(0.86, 0.80, 0.68),
	"floor": Color(0.55, 0.38, 0.24),
	"door": Color(0.45, 0.27, 0.15),
	"ceiling": Color(0.93, 0.92, 0.88),
	"wood": Color(0.50, 0.33, 0.20),
	"exterior": Color(0.82, 0.76, 0.66),
	"ground": Color(0.28, 0.42, 0.18),
	"tiles": Color(0.85, 0.87, 0.88),
}
const ROUGHNESS := {
	"wall": 0.85, "floor": 0.45, "door": 0.5, "ceiling": 0.9,
	"wood": 0.6, "exterior": 0.9, "ground": 0.95, "tiles": 0.3,
}
## If a texture slot was not downloaded, borrow another one.
const ALIAS := {"ceiling": "wall", "exterior": "wall", "tiles": "floor"}

var textures: Dictionary = {}
var sounds: Dictionary = {}
var models: Dictionary = {}
var chalk_font: Font
var has_chalk_font := false
var credits_text := ""

var _mat_cache := {}
var _color_cache := {}
var _snd_cache := {}
var _theme: Theme


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	textures = _read_json(TEX_JSON)
	sounds = _read_json(SND_JSON)
	models = _read_json(MDL_JSON)
	_load_font()
	credits_text = _read_text(CREDITS_TXT)


# ---------------------------------------------------------------- files

func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var data = JSON.parse_string(f.get_as_text())
	if data is Dictionary:
		return data
	return {}


func _read_text(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return ""
	return f.get_as_text()


# ---------------------------------------------------------------- font + theme

func _load_font() -> void:
	chalk_font = ThemeDB.fallback_font
	for p in FONT_CANDIDATES:
		if ResourceLoader.exists(p):
			var f = load(p)
			if f is Font:
				chalk_font = f
				has_chalk_font = true
				return


func get_theme() -> Theme:
	if _theme != null:
		return _theme
	var t := Theme.new()
	t.default_font = chalk_font
	t.default_font_size = 34
	t.set_stylebox("normal", "Button", _style(Color(0, 0, 0, 0.55), Color(1, 1, 1, 0.9)))
	t.set_stylebox("hover", "Button", _style(Color(0.15, 0.15, 0.15, 0.7), Color(1, 1, 1, 1)))
	t.set_stylebox("pressed", "Button", _style(Color(0.4, 0.05, 0.05, 0.85), Color(1, 1, 1, 1)))
	t.set_stylebox("disabled", "Button", _style(Color(0, 0, 0, 0.3), Color(1, 1, 1, 0.3)))
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	t.set_color("font_color", "Button", Color.WHITE)
	t.set_color("font_hover_color", "Button", Color.WHITE)
	t.set_color("font_focus_color", "Button", Color.WHITE)
	t.set_color("font_pressed_color", "Button", Color(1, 0.85, 0.85))
	t.set_color("font_outline_color", "Button", Color.BLACK)
	t.set_constant("outline_size", "Button", 6)
	t.set_color("font_color", "Label", Color.WHITE)
	t.set_color("font_outline_color", "Label", Color.BLACK)
	t.set_constant("outline_size", "Label", 8)
	var panel := _style(Color(0.04, 0.04, 0.04, 0.93), Color(1, 1, 1, 0.85))
	t.set_stylebox("panel", "Panel", panel)
	t.set_stylebox("panel", "PanelContainer", panel)
	_theme = t
	return t


func _style(bg: Color, border: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(3)
	s.set_corner_radius_all(14)
	s.content_margin_left = 24
	s.content_margin_right = 24
	s.content_margin_top = 8
	s.content_margin_bottom = 8
	return s


# ---------------------------------------------------------------- textures / materials

func _tex(path: String) -> Texture2D:
	if path == "" or not ResourceLoader.exists(path):
		return null
	var t = load(path)
	if t is Texture2D:
		return t
	return null


func _tex_info(slot: String) -> Dictionary:
	if textures.has(slot) and textures[slot] is Dictionary:
		return textures[slot]
	if ALIAS.has(slot):
		var other: String = ALIAS[slot]
		if textures.has(other) and textures[other] is Dictionary:
			return textures[other]
	return {}


func is_user_texture(slot: String) -> bool:
	var info := _tex_info(slot)
	return bool(info.get("user", false))


## PBR material (albedo + normal + roughness) for walls, floors, doors...
func get_material(slot: String) -> StandardMaterial3D:
	if _mat_cache.has(slot):
		return _mat_cache[slot]
	var m := StandardMaterial3D.new()
	var info := _tex_info(slot)
	var albedo := _tex(str(info.get("albedo", "")))
	if albedo != null:
		m.albedo_texture = albedo
		if slot == "ceiling" and not textures.has("ceiling"):
			m.albedo_color = Color(1.12, 1.12, 1.1)
	else:
		m.albedo_color = FALLBACK_COLORS.get(slot, Color(0.8, 0.8, 0.8))
	var nrm := _tex(str(info.get("normal", "")))
	if nrm != null:
		m.normal_enabled = true
		m.normal_texture = nrm
		m.normal_scale = 1.0
	var rough := _tex(str(info.get("roughness", "")))
	if rough != null:
		m.roughness_texture = rough
		m.roughness = 1.0
	else:
		m.roughness = float(ROUGHNESS.get(slot, 0.7))
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	_mat_cache[slot] = m
	return m


## The front / back picture of a door. Your own door photo is shown once
## (not repeated); a downloaded wood texture is repeated twice.
func get_door_face_material() -> StandardMaterial3D:
	if _mat_cache.has("door_face"):
		return _mat_cache["door_face"]
	var m := get_material("door").duplicate() as StandardMaterial3D
	if m.albedo_texture != null and not is_user_texture("door"):
		m.uv1_scale = Vector3(1.0, 2.0, 1.0)
	_mat_cache["door_face"] = m
	return m


func color_mat(c: Color, rough: float = 0.7, metal: float = 0.0) -> StandardMaterial3D:
	var key := "%s_%.2f_%.2f" % [c.to_html(), rough, metal]
	if _color_cache.has(key):
		return _color_cache[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	_color_cache[key] = m
	return m


func glass_mat() -> StandardMaterial3D:
	if _mat_cache.has("glass"):
		return _mat_cache["glass"]
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(0.75, 0.88, 1.0, 0.22)
	m.roughness = 0.05
	m.metallic = 0.0
	m.metallic_specular = 0.9
	_mat_cache["glass"] = m
	return m


func lamp_mat() -> StandardMaterial3D:
	if _mat_cache.has("lamp"):
		return _mat_cache["lamp"]
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(1.0, 0.97, 0.9)
	m.emission_enabled = true
	m.emission = Color(1.0, 0.92, 0.75)
	m.emission_energy_multiplier = 1.6
	_mat_cache["lamp"] = m
	return m


# ---------------------------------------------------------------- sounds

func get_sounds(sound_name: String) -> Array:
	if _snd_cache.has(sound_name):
		return _snd_cache[sound_name]
	var out: Array = []
	var list = sounds.get(sound_name, [])
	if list is Array:
		for p in list:
			var path := str(p)
			if ResourceLoader.exists(path):
				var s = load(path)
				if s is AudioStream:
					out.append(s)
	_snd_cache[sound_name] = out
	return out


func get_sound(sound_name: String) -> AudioStream:
	var arr := get_sounds(sound_name)
	if arr.is_empty():
		return null
	return arr[randi() % arr.size()]


func get_music(sound_name: String) -> AudioStream:
	var s := get_sound(sound_name)
	if s is AudioStreamMP3:
		(s as AudioStreamMP3).loop = true
	elif s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	return s


func play_2d(sound_name: String, volume_db: float = 0.0, pitch: float = 1.0) -> void:
	var s := get_sound(sound_name)
	if s == null:
		return
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)


func play_3d(sound_name: String, pos: Vector3, parent: Node, volume_db: float = 0.0, pitch: float = 1.0) -> void:
	var s := get_sound(sound_name)
	if s == null or parent == null or not parent.is_inside_tree():
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.unit_size = 5.0
	p.max_distance = 35.0
	parent.add_child(p)
	p.global_position = pos
	p.play()
	p.finished.connect(p.queue_free)


# ---------------------------------------------------------------- Sketchfab models

func has_model(key: String) -> bool:
	if not models.has(key) or not (models[key] is Dictionary):
		return false
	var path := str(models[key].get("path", ""))
	return path != "" and ResourceLoader.exists(path)


## Loads a Sketchfab model and scales it to fit `target` (width, height, depth).
## The model's bottom-centre ends up at the returned node's origin.
## mode: "fit" (fit inside the box), "height" (match height), "longest".
## Returns null if the model is not available.
func make_model(key: String, target: Vector3, mode: String = "fit", extra_yaw: float = 0.0) -> Node3D:
	if not has_model(key):
		return null
	var res = load(str(models[key].get("path", "")))
	if not (res is PackedScene):
		return null
	var node = (res as PackedScene).instantiate()
	if not (node is Node3D):
		if node != null:
			node.free()
		return null
	var inst := node as Node3D
	_strip_extras(inst)
	var aabb := calc_aabb(inst)
	if aabb.size.length() < 0.0001:
		inst.free()
		return null
	var size := aabb.size
	var yaw := extra_yaw
	# Turn the model 90 degrees if its long side does not match the target's.
	var model_long_x := size.x >= size.z
	var target_long_x := target.x >= target.z
	if model_long_x != target_long_x and absf(target.x - target.z) > 0.1 * maxf(target.x, target.z):
		yaw += PI * 0.5
		size = Vector3(size.z, size.y, size.x)
	var s := 1.0
	if mode == "height":
		s = target.y / maxf(size.y, 0.0001)
	elif mode == "longest":
		s = maxf(target.x, maxf(target.y, target.z)) / maxf(size.x, maxf(size.y, size.z))
	else:
		s = minf(target.x / maxf(size.x, 0.0001), minf(target.y / maxf(size.y, 0.0001), target.z / maxf(size.z, 0.0001)))
	var holder := Node3D.new()
	holder.name = "Model_" + key
	var pivot := Node3D.new()
	holder.add_child(pivot)
	pivot.add_child(inst)
	var center := aabb.position + aabb.size * 0.5
	inst.position = inst.position - Vector3(center.x, aabb.position.y, center.z)
	pivot.rotation.y = yaw
	pivot.scale = Vector3.ONE * s
	holder.set_meta("fitted_size", size * s)
	holder.set_meta("from_sketchfab", true)
	return holder


func model_credit(key: String) -> String:
	if not models.has(key) or not (models[key] is Dictionary):
		return ""
	var m: Dictionary = models[key]
	return "%s by %s (%s)" % [str(m.get("name", key)), str(m.get("author", "?")), str(m.get("license", "?"))]


## Bounding box of all meshes under `root`, in root's parent space.
func calc_aabb(root: Node3D) -> AABB:
	var result := AABB()
	var first := true
	var stack: Array = [[root, root.transform]]
	while stack.size() > 0:
		var item: Array = stack.pop_back()
		var node: Node = item[0]
		var xf: Transform3D = item[1]
		if node is MeshInstance3D:
			var mi := node as MeshInstance3D
			if mi.mesh != null:
				var box: AABB = xf * mi.mesh.get_aabb()
				if first:
					result = box
					first = false
				else:
					result = result.merge(box)
		for c in node.get_children():
			if c is Node3D:
				stack.append([c, xf * (c as Node3D).transform])
	return result


func _strip_extras(root: Node) -> void:
	for c in root.get_children():
		if c is Light3D or c is Camera3D:
			c.free()
		else:
			_strip_extras(c)


func set_layers_recursive(node: Node, mask: int) -> void:
	if node is VisualInstance3D:
		(node as VisualInstance3D).layers = mask
	for c in node.get_children():
		set_layers_recursive(c, mask)
