extends Node
## Read-only game database: worlds, levels, characters, weapons, power-ups, skins, enemies, bosses.

const CHARACTER_PATHS := [
	"res://resources/characters/main_ninja.tres",
	"res://resources/characters/shadow_ninja.tres",
	"res://resources/characters/samurai_ninja.tres",
	"res://resources/characters/fire_ninja.tres",
	"res://resources/characters/ice_ninja.tres",
]
const WEAPON_PATHS := [
	"res://resources/weapons/katana.tres",
	"res://resources/weapons/dual_blades.tres",
	"res://resources/weapons/shuriken.tres",
	"res://resources/weapons/bow.tres",
	"res://resources/weapons/dragon_blade.tres",
]
const POWERUP_PATHS := [
	"res://resources/powerups/double_jump.tres",
	"res://resources/powerups/shield.tres",
	"res://resources/powerups/speed_boost.tres",
	"res://resources/powerups/health_recovery.tres",
	"res://resources/powerups/critical_strike.tres",
	"res://resources/powerups/energy_boost.tres",
]
const SKIN_PATHS := [
	"res://resources/skins/original.tres",
	"res://resources/skins/crimson.tres",
	"res://resources/skins/jade.tres",
	"res://resources/skins/royal_gold.tres",
	"res://resources/skins/midnight.tres",
	"res://resources/skins/sakura.tres",
]
const LEVEL_COUNT := 24
const LEVELS_PER_WORLD := 4

const WORLDS := [
	{
		"id": 1, "name": "Bamboo Forest", "subtitle": "Where the journey begins",
		"terrain": 0, "bg": "trees", "music": "world1", "boss": "shadow_samurai",
		"modulate": Color(1, 1, 1), "sky_top": Color(0.42, 0.72, 0.95), "sky_bottom": Color(0.80, 0.93, 0.98),
		"layer_tint": Color(0.80, 1.0, 0.82), "particles": "leaf_pink",
		"elements": ["tree", "treeLong", "treePine", "treeSmall_green1", "treeSmall_green2", "bush1", "bush2"],
		"far": ["cloud1", "cloud2", "cloud3", "sun"], "decor": ["bush", "grass", "mushroom_red", "rock"],
		"light": false, "fog": Color(1, 1, 1, 0.0),
	},
	{
		"id": 2, "name": "Forgotten Village", "subtitle": "Silent streets at dusk",
		"terrain": 1, "bg": "hills", "music": "world2", "boss": "demon_ronin",
		"modulate": Color(1.0, 0.9, 0.82), "sky_top": Color(0.32, 0.22, 0.42), "sky_bottom": Color(0.98, 0.62, 0.42),
		"layer_tint": Color(0.95, 0.72, 0.62), "particles": "leaf",
		"elements": ["house1", "house2", "houseAlt1", "houseSmall1", "houseSmall2", "treeOrange", "treeLongOrange", "fence"],
		"far": ["cloud5", "cloud6", "moon"], "decor": ["fence", "fence_broken", "sign", "bush", "rock"],
		"light": true, "fog": Color(1.0, 0.6, 0.4, 0.06),
	},
	{
		"id": 3, "name": "Frozen Mountains", "subtitle": "Ice, wind and silence",
		"terrain": 2, "bg": "hills", "music": "world3", "boss": "ice_guardian",
		"modulate": Color(0.92, 0.97, 1.08), "sky_top": Color(0.52, 0.68, 0.88), "sky_bottom": Color(0.90, 0.95, 1.0),
		"layer_tint": Color(0.80, 0.90, 1.0), "particles": "snow",
		"elements": ["treeFrozen", "treePineFrozen", "treePineSnow", "treeSnow", "treeLongSnow", "treeLongFrozen"],
		"far": ["cloud1", "cloud8", "cloud2"], "decor": ["snow", "rock"],
		"light": false, "fog": Color(0.9, 0.95, 1.0, 0.10),
	},
	{
		"id": 4, "name": "Dark Temple", "subtitle": "Ancient halls of the cursed",
		"terrain": 3, "bg": "mushrooms", "music": "world4", "boss": "temple_beast",
		"modulate": Color(0.78, 0.76, 0.92), "sky_top": Color(0.06, 0.05, 0.14), "sky_bottom": Color(0.24, 0.18, 0.36),
		"layer_tint": Color(0.40, 0.36, 0.58), "particles": "spark",
		"elements": ["tower", "towerAlt", "towerSmallAlt", "treeDead", "pyramid"],
		"far": ["moonFull"], "decor": ["torch_on_a", "chain", "rock"],
		"light": true, "fog": Color(0.3, 0.2, 0.5, 0.10),
	},
	{
		"id": 5, "name": "Burning Fortress", "subtitle": "The road of ash and fire",
		"terrain": 3, "bg": "desert", "music": "world5", "boss": "fire_lord",
		"modulate": Color(1.08, 0.86, 0.76), "sky_top": Color(0.30, 0.06, 0.04), "sky_bottom": Color(0.95, 0.42, 0.16),
		"layer_tint": Color(0.75, 0.38, 0.30), "particles": "ember",
		"elements": ["castleWall", "castleWallAlt", "castleSmall", "towerSmall", "treeDead"],
		"far": ["sun"], "decor": ["torch_on_a", "rock", "cactus"],
		"light": true, "fog": Color(1.0, 0.4, 0.1, 0.08),
	},
	{
		"id": 6, "name": "Shadow Realm", "subtitle": "Where light goes to die",
		"terrain": 5, "bg": "mushrooms", "music": "world6", "boss": "shadow_king",
		"modulate": Color(0.86, 0.78, 1.0), "sky_top": Color(0.04, 0.0, 0.08), "sky_bottom": Color(0.30, 0.10, 0.42),
		"layer_tint": Color(0.42, 0.24, 0.62), "particles": "magic",
		"elements": ["treeDead", "towerAlt", "castleSmallAlt", "towerSmallAlt"],
		"far": ["moonFull"], "decor": ["grass_purple", "rock", "torch_on_a"],
		"light": true, "fog": Color(0.5, 0.2, 0.8, 0.10),
	},
]

const BOSSES := {
	"shadow_samurai": {"name": "SHADOW SAMURAI", "title": "Blade of the Bamboo Forest", "hp": 520.0, "kind": "ninja",
		"cloth_hue": 0.0, "cloth_sat": 0.25, "cloth_val": 0.35, "armor": Color(0.55, 0.15, 0.15), "scale": 1.65, "reward_coins": 400, "reward_gems": 5},
	"demon_ronin": {"name": "DEMON RONIN", "title": "The Masterless Curse", "hp": 720.0, "kind": "ninja",
		"cloth_hue": 0.99, "cloth_sat": 1.25, "cloth_val": 0.9, "armor": Color(0.95, 0.55, 0.35), "scale": 1.75, "reward_coins": 550, "reward_gems": 6},
	"ice_guardian": {"name": "ICE GUARDIAN", "title": "Keeper of the Frozen Peak", "hp": 900.0, "kind": "slime_block",
		"hue_shift": 0.0, "tint": Color(0.70, 0.92, 1.25), "scale": 3.2, "reward_coins": 700, "reward_gems": 8},
	"temple_beast": {"name": "TEMPLE BEAST", "title": "Horror of the Cursed Chamber", "hp": 1050.0, "kind": "slime_spike",
		"hue_shift": 0.0, "tint": Color(0.85, 0.75, 1.1), "scale": 3.4, "reward_coins": 850, "reward_gems": 9},
	"fire_lord": {"name": "FIRE LORD", "title": "Tyrant of the Burning Fortress", "hp": 1250.0, "kind": "slime_fire",
		"hue_shift": 0.0, "tint": Color(1.25, 0.95, 0.85), "scale": 3.6, "reward_coins": 1000, "reward_gems": 10},
	"shadow_king": {"name": "SHADOW KING", "title": "Ruler of the Shadow Realm", "hp": 1600.0, "kind": "ninja",
		"cloth_hue": 0.78, "cloth_sat": 0.9, "cloth_val": 0.45, "armor": Color(0.35, 0.25, 0.5), "scale": 1.95, "reward_coins": 2000, "reward_gems": 25},
}

## Enemy archetypes. sprite: frame set in SpriteLib, behavior: AI script.
const ENEMIES := {
	"slime": {"sprite": "slime_normal", "behavior": "walker", "hp": 30.0, "damage": 12.0, "speed": 70.0, "stomp": true, "coins": 2},
	"spike_slime": {"sprite": "slime_spike", "behavior": "walker", "hp": 45.0, "damage": 16.0, "speed": 60.0, "stomp": false, "coins": 3},
	"fire_slime": {"sprite": "slime_fire", "behavior": "walker", "hp": 50.0, "damage": 18.0, "speed": 85.0, "stomp": false, "coins": 3, "shoots": true},
	"block_slime": {"sprite": "slime_block", "behavior": "hopper", "hp": 70.0, "damage": 20.0, "speed": 120.0, "stomp": true, "coins": 4},
	"snail": {"sprite": "snail", "behavior": "walker", "hp": 40.0, "damage": 10.0, "speed": 40.0, "stomp": true, "coins": 2},
	"mouse": {"sprite": "mouse", "behavior": "charger", "hp": 25.0, "damage": 12.0, "speed": 260.0, "stomp": true, "coins": 2},
	"worm": {"sprite": "worm_normal", "behavior": "walker", "hp": 35.0, "damage": 10.0, "speed": 45.0, "stomp": true, "coins": 2},
	"ring_worm": {"sprite": "worm_ring", "behavior": "walker", "hp": 55.0, "damage": 14.0, "speed": 55.0, "stomp": true, "coins": 3},
	"ladybug": {"sprite": "ladybug", "behavior": "walker", "hp": 30.0, "damage": 12.0, "speed": 90.0, "stomp": true, "coins": 2},
	"bee": {"sprite": "bee", "behavior": "flyer", "hp": 25.0, "damage": 12.0, "speed": 110.0, "stomp": true, "coins": 3},
	"fly": {"sprite": "fly", "behavior": "chaser", "hp": 20.0, "damage": 10.0, "speed": 140.0, "stomp": true, "coins": 3},
	"frog": {"sprite": "frog", "behavior": "jumper", "hp": 35.0, "damage": 14.0, "speed": 160.0, "stomp": true, "coins": 3},
	"barnacle": {"sprite": "barnacle", "behavior": "chomper", "hp": 60.0, "damage": 18.0, "speed": 0.0, "stomp": false, "coins": 4},
	"fish": {"sprite": "fish", "behavior": "leaper", "hp": 30.0, "damage": 16.0, "speed": 0.0, "stomp": false, "coins": 3},
	"ninja": {"sprite": "ninja", "behavior": "ninja", "hp": 55.0, "damage": 16.0, "speed": 150.0, "stomp": false, "coins": 5,
		"cloth_hue": 0.0, "cloth_sat": 0.0, "cloth_val": 0.55},
	"kunai_ninja": {"sprite": "ninja", "behavior": "thrower", "hp": 45.0, "damage": 14.0, "speed": 120.0, "stomp": false, "coins": 6,
		"cloth_hue": 0.58, "cloth_sat": 0.7, "cloth_val": 0.6},
	"elite_ninja": {"sprite": "ninja", "behavior": "ninja", "hp": 95.0, "damage": 24.0, "speed": 190.0, "stomp": false, "coins": 10,
		"cloth_hue": 0.0, "cloth_sat": 1.2, "cloth_val": 0.75},
}

var characters: Array[CharacterData] = []
var weapons: Array[WeaponData] = []
var powerups: Array[PowerupData] = []
var skins: Array[SkinData] = []
var levels: Array[LevelData] = []

var _character_map := {}
var _weapon_map := {}
var _powerup_map := {}
var _skin_map := {}


func _ready() -> void:
	for p in CHARACTER_PATHS:
		var c: CharacterData = load(p)
		characters.append(c)
		_character_map[c.id] = c
	for p in WEAPON_PATHS:
		var w: WeaponData = load(p)
		weapons.append(w)
		_weapon_map[w.id] = w
	for p in POWERUP_PATHS:
		var u: PowerupData = load(p)
		powerups.append(u)
		_powerup_map[u.id] = u
	for p in SKIN_PATHS:
		var s: SkinData = load(p)
		skins.append(s)
		_skin_map[s.id] = s
	for i in range(1, LEVEL_COUNT + 1):
		levels.append(load("res://resources/levels/level_%02d.tres" % i))


func character(id: String) -> CharacterData:
	return _character_map.get(id, characters[0])


func weapon(id: String) -> WeaponData:
	return _weapon_map.get(id, weapons[0])


func powerup(id: String) -> PowerupData:
	return _powerup_map.get(id)


func skin(id: String) -> SkinData:
	return _skin_map.get(id, skins[0])


func level(index: int) -> LevelData:
	return levels[clampi(index, 1, LEVEL_COUNT) - 1]


func world(id: int) -> Dictionary:
	return WORLDS[clampi(id, 1, WORLDS.size()) - 1]


func world_of_level(index: int) -> Dictionary:
	return world(level(index).world)


func is_boss_level(index: int) -> bool:
	return index % LEVELS_PER_WORLD == 0
