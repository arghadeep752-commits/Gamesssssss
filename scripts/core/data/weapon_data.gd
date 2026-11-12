class_name WeaponData
extends Resource
## Weapon definition. Add a new weapon by creating another .tres with this script.

@export var id: String = ""
@export var display_name: String = ""
@export_multiline var description: String = ""
@export var icon: Texture2D
## "melee" or "ranged"
@export var kind: String = "melee"
@export var base_damage: float = 20.0
@export var damage_per_level: float = 5.0
@export var max_level: int = 5
@export var attack_cooldown: float = 0.32
@export var attack_speed: float = 1.0
@export var reach: Vector2 = Vector2(86, 70)
@export var hits_per_attack: int = 1
## Projectile scene key used by ranged weapons ("shuriken", "arrow", "kunai").
@export var projectile: String = ""
@export var projectile_speed: float = 900.0
@export var effect_color: Color = Color(1, 1, 1, 1)
## Weapon ability bound to the weapon-ability button.
@export var ability_id: String = "dash_slash"
@export var ability_name: String = ""
@export var ability_cooldown: float = 3.0
@export var unlock_type: String = "default"
@export var unlock_level: int = 0
@export var price_coins: int = 0
@export var price_gems: int = 0
@export var upgrade_base_cost: int = 250


func damage_at(level: int) -> float:
	return base_damage + damage_per_level * float(max(0, level - 1))


func upgrade_cost(level: int) -> int:
	return int(upgrade_base_cost * pow(1.6, max(0, level - 1)))
