class_name Mats
extends RefCounted
## Builds the house materials from real photo-scanned PBR texture sets (Poly Haven / ambientCG, CC0 - photographed
## surfaces, nothing AI generated), downloaded at build time into res://assets/downloaded/tex/<slot>/: colour (diff),
## normal (nor), roughness (rough) and ambient occlusion (ao).

const TEX := "res://assets/downloaded/tex/"

# tint multiplies the photo (old, dark, dusty); color is used when a slot has no texture
const TABLE := {
	"floor_wood": {"slot": ["wood_floor_old", "wood_floor"], "tint": Color(0.62, 0.55, 0.5), "rough": 0.95, "color": Color(0.30, 0.2, 0.12), "ao": true},
	"floor_stone": {"slot": ["stone_slab", "stone_floor"], "tint": Color(0.62, 0.6, 0.58), "rough": 0.9, "color": Color(0.35, 0.33, 0.3), "ao": true},
	"wall_wood": {"slot": ["wood_panel", "wood_wall"], "tint": Color(0.55, 0.48, 0.42), "rough": 1.0, "color": Color(0.22, 0.14, 0.09), "ao": true},
	"wall_plaster": {"slot": ["plaster_old", "plaster"], "tint": Color(0.72, 0.66, 0.56), "rough": 1.0, "color": Color(0.45, 0.4, 0.33), "ao": true},
	# the old Indian house: lime plaster in the colours of each room, its own floor in each room
	"wall_plaster_blue": {"slot": ["plaster_blue", "plaster"], "tint": Color(0.7, 0.72, 0.78), "rough": 1.0, "color": Color(0.3, 0.38, 0.45), "ao": true},
	"wall_plaster_yellow": {"slot": ["plaster_yellow", "plaster"], "tint": Color(0.78, 0.68, 0.5), "rough": 1.0, "color": Color(0.55, 0.45, 0.25), "ao": true},
	"wall_plaster_red": {"slot": ["plaster_red", "plaster"], "tint": Color(0.75, 0.6, 0.55), "rough": 1.0, "color": Color(0.5, 0.18, 0.12), "ao": true},
	"wall_plaster_white": {"slot": ["plaster_white", "plaster"], "tint": Color(0.68, 0.64, 0.58), "rough": 1.0, "color": Color(0.55, 0.52, 0.47), "ao": true},
	"floor_terracotta": {"slot": ["floor_terracotta", "stone_slab", "stone_floor"], "tint": Color(0.7, 0.62, 0.56), "rough": 0.85, "color": Color(0.45, 0.22, 0.14), "ao": true},
	"floor_redtile": {"slot": ["floor_redtile", "stone_slab", "stone_floor"], "tint": Color(0.68, 0.6, 0.55), "rough": 0.85, "color": Color(0.42, 0.18, 0.12), "ao": true},
	"floor_checker": {"slot": ["floor_checker", "stone_slab", "stone_floor"], "tint": Color(0.66, 0.63, 0.6), "rough": 0.7, "color": Color(0.35, 0.33, 0.3), "ao": true},
	"floor_clay": {"slot": ["floor_clay", "clay_pbr", "clay"], "tint": Color(0.66, 0.6, 0.54), "rough": 1.0, "color": Color(0.4, 0.3, 0.22), "ao": true},
	"beam_wood": {"slot": ["wood_beam", "wood_dark"], "tint": Color(0.5, 0.43, 0.37), "rough": 0.9, "color": Color(0.18, 0.11, 0.07), "ao": true},
	"pillar_wood": {"slot": ["wood_carved", "wood_dark"], "tint": Color(0.55, 0.42, 0.33), "rough": 0.7, "color": Color(0.2, 0.12, 0.07), "ao": true},
	"stone_base": {"slot": ["stone_slab", "stone_floor"], "tint": Color(0.7, 0.67, 0.62), "rough": 0.85, "color": Color(0.42, 0.4, 0.37), "ao": true},
	"shutter_wood": {"slot": ["wood_shutter", "wood_door"], "tint": Color(0.6, 0.52, 0.45), "rough": 0.9, "color": Color(0.25, 0.17, 0.1), "ao": true},
	"ceiling_wood": {"slot": ["ceiling_planks", "wood_ceiling"], "tint": Color(0.45, 0.4, 0.36), "rough": 1.0, "color": Color(0.2, 0.13, 0.08), "ao": true},
	"trim_wood": {"slot": ["trim_dark", "wood_dark"], "tint": Color(0.5, 0.42, 0.36), "rough": 0.8, "color": Color(0.16, 0.1, 0.06)},
	"door_wood": {"slot": ["wood_studded", "wood_door"], "tint": Color(0.58, 0.48, 0.4), "rough": 0.85, "color": Color(0.2, 0.12, 0.07)},
	"brass": {"slot": "brass", "tint": Color(1.0, 0.82, 0.5), "rough": 0.45, "metal": 0.9, "color": Color(0.8, 0.6, 0.2)},
	"stone_altar": {"slot": ["stone_slab", "stone_floor"], "tint": Color(0.75, 0.7, 0.66), "rough": 0.8, "color": Color(0.5, 0.45, 0.4)},
	"red_cloth": {"slot": ["cloth_red", "hessian", "fiber"], "tint": Color(0.95, 0.35, 0.3), "rough": 1.0, "color": Color(0.6, 0.05, 0.05)},
	"clay": {"slot": ["clay_pbr", "clay"], "tint": Color(0.66, 0.36, 0.24), "rough": 1.0, "color": Color(0.45, 0.22, 0.13)},
	"coconut": {"slot": ["husk"], "tint": Color(0.62, 0.42, 0.26), "rough": 0.95, "color": Color(0.27, 0.16, 0.08)},
	"kumkum_red": {"slot": ["powder"], "tint": Color(1.0, 0.16, 0.12), "rough": 1.0, "color": Color(0.8, 0.04, 0.03)},
	"camphor_white": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.6, "color": Color(0.92, 0.92, 0.88)},
	"copper": {"slot": "copper", "tint": Color(1.0, 0.6, 0.4), "rough": 0.4, "metal": 0.9, "color": Color(0.72, 0.4, 0.25)},
	"leaf_green": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.7, "color": Color(0.14, 0.32, 0.1), "double": true},
	"lantern_metal": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.6, "metal": 0.8, "color": Color(0.1, 0.09, 0.08)},
	"lantern_glow": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.5, "color": Color(1.0, 0.6, 0.25), "emit": 3.0},
	"rope": {"slot": ["hessian", "fiber"], "tint": Color(0.85, 0.72, 0.52), "rough": 1.0, "color": Color(0.45, 0.35, 0.22)},
	"sack": {"slot": ["hessian", "fiber"], "tint": Color(0.9, 0.8, 0.62), "rough": 1.0, "color": Color(0.55, 0.45, 0.3)},
	"iron": {"slot": "copper", "tint": Color(0.32, 0.3, 0.28), "rough": 0.7, "metal": 0.6, "color": Color(0.12, 0.11, 0.1)},
	"wood_old": {"slot": ["trim_dark", "wood_dark"], "tint": Color(0.62, 0.52, 0.42), "rough": 0.85, "color": Color(0.25, 0.16, 0.1)},
	"candle_wax": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.45, "color": Color(0.93, 0.87, 0.74)},
	"wick": {"slot": "", "tint": Color(1, 1, 1), "rough": 1.0, "color": Color(0.04, 0.035, 0.03)},
	"wick_ember": {"slot": "", "tint": Color(1, 1, 1), "rough": 1.0, "color": Color(1.0, 0.35, 0.08), "emit": 3.0},
	# the detailed ritual items (tools/hero_items.py)
	"coir": {"slot": ["husk"], "tint": Color(0.75, 0.55, 0.35), "rough": 1.0, "color": Color(0.46, 0.3, 0.15), "double": true},
	"coconut_dark": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.9, "color": Color(0.1, 0.06, 0.035)},
	"thread_red": {"slot": ["hessian", "fiber"], "tint": Color(0.9, 0.1, 0.07), "rough": 0.95, "color": Color(0.7, 0.04, 0.03)},
	"thread_yellow": {"slot": ["hessian", "fiber"], "tint": Color(1.0, 0.78, 0.2), "rough": 0.95, "color": Color(0.9, 0.65, 0.1)},
	"oil": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.06, "color": Color(0.3, 0.19, 0.04)},
	"water": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.04, "color": Color(0.06, 0.09, 0.1)},
	"wick_cotton": {"slot": ["hessian", "fiber"], "tint": Color(1.0, 0.96, 0.88), "rough": 1.0, "color": Color(0.9, 0.86, 0.76)},
	"rice": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.55, "color": Color(0.95, 0.93, 0.86)},
}

static var _cache := {}

static func _load_tex(slot: String, kind: String) -> Texture2D:
	for ext in [".jpg", ".png", ".jpeg"]:
		var p: String = TEX + slot + "/" + kind + ext
		if ResourceLoader.exists(p):
			var t = load(p)
			if t is Texture2D:
				return t
	return null

static func get_material(mat_name: String) -> StandardMaterial3D:
	if _cache.has(mat_name):
		return _cache[mat_name]
	var d: Dictionary = TABLE.get(mat_name, {"slot": "", "tint": Color(1, 1, 1), "rough": 0.9, "color": Color(0.5, 0.5, 0.5)})
	var m := StandardMaterial3D.new()
	m.resource_name = mat_name
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	m.roughness = float(d.get("rough", 0.9))
	m.metallic = float(d.get("metal", 0.0))
	m.metallic_specular = 0.5          # physically based: 4% reflectance for wood, plaster, clay, stone
	var slots: Array = d.get("slot", "") if d.get("slot", "") is Array else [d.get("slot", "")]
	var slot := ""
	var diff: Texture2D = null
	for sl in slots:
		if String(sl) != "":
			diff = _load_tex(String(sl), "diff")
			if diff:
				slot = String(sl)
				break
	if diff:
		m.albedo_texture = diff
		m.albedo_color = d["tint"]
		var nor := _load_tex(slot, "nor")
		if nor:
			m.normal_enabled = true
			m.normal_texture = nor
			m.normal_scale = 1.0
		var rg := _load_tex(slot, "rough")
		if rg:
			m.roughness_texture = rg
			m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
			m.roughness = clampf(float(d.get("rough", 0.9)), 0.0, 1.0)
		var ao := _load_tex(slot, "ao")
		if ao:
			m.ao_enabled = true
			m.ao_texture = ao
			m.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
			m.ao_light_affect = 0.45           # the cracks and grooves stay dark under the lamps too
	else:
		m.albedo_color = d["color"]
	if d.get("ao", false):
		m.vertex_color_use_as_albedo = true      # baked ambient occlusion from Blender
	if d.get("double", false):
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
	if d.has("emit"):
		m.emission_enabled = true
		m.emission = d["color"]
		m.emission_energy_multiplier = float(d["emit"])
	_cache[mat_name] = m
	return m
