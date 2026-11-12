extends Node
## Builds and caches SpriteFrames for the artist sprite sheets used in the game.

const NINJA_DIR := "res://assets/characters/ninja/"
const ENEMY_DIR := "res://assets/enemies/"
const BOSS_DIR := "res://assets/bosses/"
const FX_SHADER := preload("res://shaders/sprite_fx.gdshader")

## Kenney creature frame sets (all face left in the source art).
const CRITTERS := {
	"slime_normal": {"move": ["slime_normal_walk_a", "slime_normal_walk_b"], "idle": ["slime_normal_rest"], "hurt": ["slime_normal_flat"]},
	"slime_spike": {"move": ["slime_spike_walk_a", "slime_spike_walk_b"], "idle": ["slime_spike_rest"], "hurt": ["slime_spike_flat"]},
	"slime_fire": {"move": ["slime_fire_walk_a", "slime_fire_walk_b"], "idle": ["slime_fire_rest"], "hurt": ["slime_fire_flat"]},
	"slime_block": {"move": ["slime_block_walk_a", "slime_block_walk_b"], "idle": ["slime_block_rest"], "jump": ["slime_block_jump"], "hurt": ["slime_block_rest"]},
	"snail": {"move": ["snail_walk_a", "snail_walk_b"], "idle": ["snail_rest"], "hurt": ["snail_shell"]},
	"mouse": {"move": ["mouse_walk_a", "mouse_walk_b"], "idle": ["mouse_rest"]},
	"worm_normal": {"move": ["worm_normal_move_a", "worm_normal_move_b"], "idle": ["worm_normal_rest"]},
	"worm_ring": {"move": ["worm_ring_move_a", "worm_ring_move_b"], "idle": ["worm_ring_rest"]},
	"ladybug": {"move": ["ladybug_walk_a", "ladybug_walk_b"], "idle": ["ladybug_rest"], "jump": ["ladybug_fly"]},
	"bee": {"move": ["bee_a", "bee_b"], "idle": ["bee_rest"]},
	"fly": {"move": ["fly_a", "fly_b"], "idle": ["fly_rest"]},
	"frog": {"move": ["frog_idle"], "idle": ["frog_idle"], "jump": ["frog_jump"]},
	"barnacle": {"move": ["barnacle_attack_rest"], "idle": ["barnacle_attack_rest"], "attack": ["barnacle_attack_a", "barnacle_attack_b"]},
	"fish": {"move": ["fish_purple_up", "fish_purple_down"], "idle": ["fish_purple_rest"]},
	"saw": {"move": ["saw_a", "saw_b"], "idle": ["saw_rest"]},
}

var ninja_meta := {}
var _cache := {}
var _tex := {}


func _ready() -> void:
	var f := FileAccess.open(NINJA_DIR + "ninja_frames.json", FileAccess.READ)
	if f:
		ninja_meta = JSON.parse_string(f.get_as_text())


func tex(path: String) -> Texture2D:
	if not _tex.has(path):
		_tex[path] = load(path) if ResourceLoader.exists(path) else null
	return _tex[path]


func ninja_frames() -> SpriteFrames:
	if _cache.has("ninja"):
		return _cache["ninja"]
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	for anim in ninja_meta.keys():
		if anim.begins_with("_"):
			continue
		var m: Dictionary = ninja_meta[anim]
		var t := tex(NINJA_DIR + anim + ".png")
		var frames := []
		for i in int(m.frames):
			var at := AtlasTexture.new()
			at.atlas = t
			at.region = Rect2(i * int(m.w), 0, int(m.w), int(m.h))
			frames.append(at)
		match anim:
			"jump":
				_add(sf, "jump", frames.slice(0, 5), m.fps, false)
				_add(sf, "fall", frames.slice(5, 10), 10, true)
				_add(sf, "victory", frames, 12, true)
			"dead":
				_add(sf, "dead", frames, m.fps, false)
				_add(sf, "hurt", frames.slice(0, 3), 14, false)
			_:
				_add(sf, anim, frames, m.fps, m.loop)
	_cache["ninja"] = sf
	return sf


func ninja_cell_height() -> float:
	return float(ninja_meta.get("idle", {}).get("h", 138))


func ninja_foot_margin() -> float:
	return float(ninja_meta.get("_foot_margin", 4))


func _add(sf: SpriteFrames, name: String, frames: Array, fps: float, loop: bool) -> void:
	sf.add_animation(name)
	sf.set_animation_speed(name, fps)
	sf.set_animation_loop(name, loop)
	for fr in frames:
		sf.add_frame(name, fr)


func critter_frames(kind: String, big := false) -> SpriteFrames:
	var key := kind + ("_big" if big else "")
	if _cache.has(key):
		return _cache[key]
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	var def: Dictionary = CRITTERS.get(kind, CRITTERS["slime_normal"])
	var dir := BOSS_DIR if big else ENEMY_DIR
	for anim in ["move", "idle", "hurt", "jump", "attack"]:
		var names: Array = def.get(anim, def.get("idle"))
		var frames := []
		for n in names:
			var t := tex(dir + n + ".png")
			if t == null:
				t = tex(ENEMY_DIR + n + ".png")
			frames.append(t)
		_add(sf, anim, frames, 6.0 if anim == "move" else 8.0, true)
	_cache[key] = sf
	return sf


func strip_frames(path: String, frame_w: int, fps := 12.0, loop := true) -> SpriteFrames:
	var key := "%s:%d" % [path, frame_w]
	if _cache.has(key):
		return _cache[key]
	var t := tex(path)
	var sf := SpriteFrames.new()
	var count: int = max(1, int(t.get_width() / frame_w))
	sf.set_animation_speed("default", fps)
	sf.set_animation_loop("default", loop)
	for i in count:
		var at := AtlasTexture.new()
		at.atlas = t
		at.region = Rect2(i * frame_w, 0, frame_w, t.get_height())
		sf.add_frame("default", at)
	_cache[key] = sf
	return sf


func make_fx_material(cloth_hue := -1.0, cloth_sat := 1.0, cloth_val := 1.0, armor := Color.WHITE, hue_shift := 0.0, gsat := 1.0) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = FX_SHADER
	m.set_shader_parameter("cloth_hue", cloth_hue)
	m.set_shader_parameter("cloth_sat", cloth_sat)
	m.set_shader_parameter("cloth_val", cloth_val)
	m.set_shader_parameter("armor_tint", armor)
	m.set_shader_parameter("global_hue_shift", hue_shift)
	m.set_shader_parameter("global_sat", gsat)
	m.set_shader_parameter("flash_amount", 0.0)
	return m


func material_for_character(c: CharacterData) -> ShaderMaterial:
	var skin_id := SaveManager.equipped_skin(c.id)
	if skin_id != "" and skin_id != "original":
		var s := GameData.skin(skin_id)
		return make_fx_material(s.cloth_hue, s.cloth_saturation, s.cloth_value, s.armor_tint)
	return make_fx_material(c.cloth_hue, c.cloth_saturation, c.cloth_value, c.armor_tint)
