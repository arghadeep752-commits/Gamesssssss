class_name CharacterData
extends Resource
## Playable character definition (data-driven, edit the .tres files in res://resources/characters).

@export var id: String = ""
@export var display_name: String = ""
@export_multiline var description: String = ""
## Palette swap of the ninja's cloth (hue 0..1, -1 keeps the artist's original purple).
@export var cloth_hue: float = -1.0
@export var cloth_saturation: float = 1.0
@export var cloth_value: float = 1.0
@export var armor_tint: Color = Color(1, 1, 1, 1)
## Visual aura: "", "shadow", "fire", "ice", "gold"
@export var aura: String = ""
@export var max_health: float = 100.0
@export var move_speed: float = 340.0
@export var jump_velocity: float = 960.0
@export var damage_multiplier: float = 1.0
@export var defense: float = 0.0
@export var special_id: String = "kunai_barrage"
@export var special_name: String = ""
@export_multiline var special_description: String = ""
## "default", "level" (complete level_value), "coins", "gems"
@export var unlock_type: String = "default"
@export var unlock_level: int = 0
@export var price_coins: int = 0
@export var price_gems: int = 0
@export var theme_color: Color = Color(0.6, 0.3, 0.8)
