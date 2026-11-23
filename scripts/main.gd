extends Node3D
## The level: one room with a locked door. Connects the player, the door and the on-screen controls.

@onready var player: CharacterBody3D = $Player
@onready var door: StaticBody3D = $Door
@onready var hud: CanvasLayer = $HUD


func _ready() -> void:
	hud.player = player
	door.tried_locked.connect(_on_door_tried_locked)


func _on_door_tried_locked() -> void:
	hud.show_message("The door is locked.")
