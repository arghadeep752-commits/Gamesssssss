class_name PowerupData
extends Resource
## Power-up definition (in-level pickups and shop consumables).

@export var id: String = ""
@export var display_name: String = ""
@export_multiline var description: String = ""
@export var icon: Texture2D
@export var color: Color = Color.WHITE
## Seconds the effect lasts. 0 = instant.
@export var duration: float = 10.0
@export var magnitude: float = 1.0
@export var shop_price_coins: int = 150
@export var shop_price_gems: int = 0
