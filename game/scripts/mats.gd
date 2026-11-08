class_name Mats
extends RefCounted
## Builds the house materials from real photographic PBR textures (Poly Haven / ambientCG, CC0), downloaded at
## build time into res://assets/downloaded/tex/<slot>/{diff,nor,rough}.(jpg|png).

const TEX := "res://assets/downloaded/tex/"

# tint multiplies the photo (old, dark, dusty); color is used when a slot has no texture
const TABLE := {
	"floor_wood": {"slot": "wood_floor", "tint": Color(0.62, 0.55, 0.5), "rough": 0.95, "color": Color(0.30, 0.2, 0.12), "ao": true},
	"floor_stone": {"slot": "stone_floor", "tint": Color(0.62, 0.6, 0.58), "rough": 0.9, "color": Color(0.35, 0.33, 0.3), "ao": true},
	"wall_wood": {"slot": "wood_wall", "tint": Color(0.5, 0.45, 0.4), "rough": 1.0, "color": Color(0.22, 0.14, 0.09), "ao": true},
	"wall_plaster": {"slot": "plaster", "tint": Color(0.66, 0.6, 0.5), "rough": 1.0, "color": Color(0.45, 0.4, 0.33), "ao": true},
	"ceiling_wood": {"slot": "wood_ceiling", "tint": Color(0.45, 0.4, 0.36), "rough": 1.0, "color": Color(0.2, 0.13, 0.08), "ao": true},
	"trim_wood": {"slot": "wood_dark", "tint": Color(0.5, 0.42, 0.36), "rough": 0.8, "color": Color(0.16, 0.1, 0.06)},
	"door_wood": {"slot": "wood_door", "tint": Color(0.55, 0.46, 0.38), "rough": 0.85, "color": Color(0.2, 0.12, 0.07)},
	"brass": {"slot": "brass", "tint": Color(1.0, 0.82, 0.5), "rough": 0.45, "metal": 0.9, "color": Color(0.8, 0.6, 0.2)},
	"stone_altar": {"slot": "stone_floor", "tint": Color(0.75, 0.7, 0.66), "rough": 0.8, "color": Color(0.5, 0.45, 0.4)},
	"red_cloth": {"slot": "fiber", "tint": Color(0.8, 0.1, 0.08), "rough": 1.0, "color": Color(0.6, 0.05, 0.05)},
	"clay": {"slot": "clay", "tint": Color(0.9, 0.55, 0.4), "rough": 1.0, "color": Color(0.55, 0.28, 0.16)},
	"coconut": {"slot": "fiber", "tint": Color(0.75, 0.55, 0.38), "rough": 1.0, "color": Color(0.32, 0.2, 0.1)},
	"kumkum_red": {"slot": "", "tint": Color(1, 1, 1), "rough": 1.0, "color": Color(0.8, 0.04, 0.03)},
	"camphor_white": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.6, "color": Color(0.92, 0.92, 0.88)},
	"copper": {"slot": "copper", "tint": Color(1.0, 0.6, 0.4), "rough": 0.4, "metal": 0.9, "color": Color(0.72, 0.4, 0.25)},
	"leaf_green": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.7, "color": Color(0.14, 0.32, 0.1), "double": true},
	"lantern_metal": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.6, "metal": 0.8, "color": Color(0.1, 0.09, 0.08)},
	"lantern_glow": {"slot": "", "tint": Color(1, 1, 1), "rough": 0.5, "color": Color(1.0, 0.6, 0.25), "emit": 2.2},
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
	m.metallic_specular = 0.35
	var slot: String = d.get("slot", "")
	var diff: Texture2D = _load_tex(slot, "diff") if slot != "" else null
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
