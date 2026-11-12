class_name LevelData
extends Resource
## One campaign level. Layout = ordered list of hand-made chunks from ChunkLibrary,
## followed by the level's own unique set-piece rows (signature) where present.

@export var index: int = 1
@export var world: int = 1
@export var display_name: String = ""
@export var chunks: PackedStringArray = PackedStringArray()
@export var difficulty: float = 1.0
@export var enemy_pool: PackedStringArray = PackedStringArray()
@export var boss_id: String = ""
@export var par_time: float = 120.0
@export var objective: String = "Reach the exit gate"
