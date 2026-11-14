class_name Mats
extends RefCounted
## Surfaces of the school: a photographed texture per material, tinted to its paint colour, lit by the lightmap baked in Blender.

const TEX_DIR := "res://assets/downloaded/tex/"
# material -> [photo slot, how much of the paint colour replaces the photo's own colour]
const MAP := {
	"plaster": ["plaster", 0.75], "plaster_ext": ["plaster_rough", 0.8], "ceiling": ["plaster", 0.85], "plinth": ["plaster_rough", 0.85],
	"floor_cement": ["concrete_floor", 0.35], "floor_terrazzo": ["terrazzo", 0.3], "floor_tiles": ["tiles_white", 0.2],
	"floor_kota": ["stone_floor", 0.5], "floor_veranda": ["red_tiles", 0.45], "dado_green": ["paint_chipped", 0.9],
	"dado_blue": ["paint_chipped", 0.9], "dado_red": ["paint_chipped", 0.9], "dado_brown": ["paint_chipped", 0.9],
	"dado_tiles": ["tiles_white", 0.2], "wood": ["wood", 0.6], "wood_dark": ["wood", 0.85], "wood_old": ["wood_old", 0.4],
	"wood_painted_blue": ["wood_painted", 0.9], "wood_painted_green": ["wood_painted", 0.9], "wood_door_main": ["wood_old", 0.7],
	"wood_plank": ["wood_old", 0.35], "wood_handle": ["wood", 0.6], "metal_green": ["metal_painted", 0.9],
	"metal_grey": ["metal_painted", 0.92], "metal_white": ["metal_painted", 0.95], "rust": ["rust", 0.25],
	"steel": ["metal_brushed", 0.7], "steel_face": ["metal_brushed", 0.7], "aluminium": ["metal_brushed", 0.6],
	"aluminium_soot": ["metal_brushed", 0.9], "brass": ["metal_brushed", 0.92], "iron_old": ["rust", 0.8],
	"chalkboard": ["slate", 0.85], "concrete": ["concrete", 0.3], "concrete_wet": ["concrete", 0.6], "ground_dirt": ["ground_dirt", 0.3],
	"ground_court": ["ground_court", 0.4], "brick_path": ["brick", 0.4], "brick_soot": ["brick", 0.85], "roof": ["concrete", 0.5],
	"sack": ["hessian", 0.4], "fabric_mat": ["hessian", 0.7], "curtain": ["fabric", 0.92], "felt": ["fabric", 0.95],
	"felt_green": ["fabric", 0.95], "file_cloth": ["fabric", 0.95], "bark": ["bark", 0.3], "cardboard": ["cardboard", 0.5],
	"paper": ["cardboard", 0.97], "register_red": ["cardboard", 0.95], "register_blue": ["cardboard", 0.95], "book_red": ["cardboard", 0.95],
	"book_blue": ["cardboard", 0.95], "book_green": ["cardboard", 0.95], "book_brown": ["cardboard", 0.9], "book_black": ["cardboard", 0.97],
	"clay": ["concrete", 0.92], "ceramic": ["tiles_white", 0.9], "ash": ["concrete", 0.6], "broom": ["hessian", 0.6],
	"rope": ["hessian", 0.7], "cane": ["wood", 0.8], "tag_white": ["cardboard", 0.95], "tag_yellow": ["cardboard", 0.95],
}
const TWO_SIDED := ["leaves", "curtain", "paper", "tag_white", "tag_yellow", "glass", "glass_dirty"]

static var _tex := {}
static var _shader: Shader
static var _white: ImageTexture
static var _leaf: ImageTexture
static var base_colors := {}
static var emit := {}

const SHADER_CODE := """
shader_type spatial;
render_mode unshaded, CULL;
uniform sampler2D tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D lm : source_color, filter_linear, repeat_disable;
uniform vec3 base = vec3(0.5);
uniform float tint = 1.0;
uniform float lm_gain = 4.0;
uniform vec3 flat_light = vec3(0.0);
uniform float use_lm = 1.0;
uniform vec3 ambient = vec3(0.012, 0.014, 0.02);
uniform float glow = 0.0;
uniform float cutout = 0.0;
void fragment() {
	vec4 t4 = texture(tex, UV);
	if (cutout > 0.5 && t4.a < 0.5) { discard; }
	vec3 t = t4.rgb;
	float avg = dot(textureLod(tex, UV, 9.0).rgb, vec3(0.3333));
	float l = dot(t, vec3(0.3333)) / max(avg, 0.03);
	vec3 c = mix(t, base * clamp(l, 0.0, 2.2), tint);
	vec3 light = mix(flat_light, texture(lm, UV2).rgb * lm_gain, use_lm) + ambient;
	ALBEDO = c * light + base * glow;
}
"""
static var _shader_ds: Shader


static func setup(meta: Dictionary) -> void:
	base_colors = meta.get("base_colors", {})
	emit = meta.get("emit", {})
	if _shader == null:
		_shader = Shader.new()
		_shader.code = SHADER_CODE.replace("CULL", "cull_back")
		_shader_ds = Shader.new()
		_shader_ds.code = SHADER_CODE.replace("CULL", "cull_disabled")
		var img := Image.create(4, 4, false, Image.FORMAT_RGB8)
		img.fill(Color(1, 1, 1))
		_white = ImageTexture.create_from_image(img)
		_leaf = _make_leaves()


static func _make_leaves() -> ImageTexture:
	# neem leaflets: thin pointed ovals along a few twigs, with alpha (drawn here)
	var n := 128
	var img := Image.create(n, n, true, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for k in 90:
		var cx := rng.randf_range(8, n - 8)
		var cy := rng.randf_range(8, n - 8)
		var ang := rng.randf_range(0, PI)
		var ln := rng.randf_range(7, 13)
		var wd := rng.randf_range(1.6, 2.8)
		var g := rng.randf_range(0.55, 1.0)
		for i in range(-14, 15):
			for j in range(-14, 15):
				var x := float(i) * cos(ang) + float(j) * sin(ang)
				var y := -float(i) * sin(ang) + float(j) * cos(ang)
				if abs(x) < ln and abs(y) < wd * (1.0 - abs(x) / ln):
					var px := int(cx) + i
					var py := int(cy) + j
					if px >= 0 and px < n and py >= 0 and py < n:
						img.set_pixel(px, py, Color(0.5 * g, 0.75 * g, 0.35 * g, 1))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


static func photo(slot: String) -> Texture2D:
	if _tex.has(slot):
		return _tex[slot]
	var t: Texture2D = _white
	for ext in ["jpg", "png"]:
		var p: String = TEX_DIR + slot + "/diff." + String(ext)
		if ResourceLoader.exists(p):
			t = load(p)
			break
	_tex[slot] = t
	return t


static func color_of(mat: String) -> Color:
	var c = base_colors.get(mat, [0.5, 0.5, 0.5])
	return Color(c[0], c[1], c[2])


## lightmap: baked texture or null; flat: light colour used when there is no lightmap;
## own: the model's own colour texture (Hyper3D models), used as it is instead of a photo
static func make(mat: String, lightmap: Texture2D, flat: Color, gain: float, own: Texture2D = null) -> Material:
	if mat == "glass" or mat == "glass_dirty":
		var g := StandardMaterial3D.new()
		g.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		g.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		g.albedo_color = Color(0.25, 0.32, 0.34, 0.22 if mat == "glass" else 0.4)
		g.cull_mode = BaseMaterial3D.CULL_DISABLED
		return g
	var m := ShaderMaterial.new()
	m.shader = _shader_ds if mat in TWO_SIDED else _shader
	var info = MAP.get(mat, ["", 1.0])
	var c := color_of(mat)
	if own != null:
		m.set_shader_parameter("tex", own)
		m.set_shader_parameter("tint", 0.0)
		m.set_shader_parameter("base", Vector3(0.5, 0.5, 0.5))
	elif mat == "leaves":
		m.set_shader_parameter("tex", _leaf)
		m.set_shader_parameter("tint", 0.0)
		m.set_shader_parameter("cutout", 1.0)
		m.set_shader_parameter("base", Vector3(0.3, 0.45, 0.2))
	else:
		m.set_shader_parameter("tex", photo(info[0]) if info[0] != "" else _white)
		m.set_shader_parameter("tint", info[1])
		m.set_shader_parameter("base", Vector3(c.r, c.g, c.b))
	if lightmap != null:
		m.set_shader_parameter("lm", lightmap)
		m.set_shader_parameter("use_lm", 1.0)
	else:
		m.set_shader_parameter("lm", _white)
		m.set_shader_parameter("use_lm", 0.0)
	m.set_shader_parameter("flat_light", Vector3(flat.r, flat.g, flat.b))
	m.set_shader_parameter("lm_gain", gain)
	m.set_shader_parameter("glow", float(emit.get(mat, 0.0)) * 0.25)
	return m
