extends Node
## Global signal bus + input map registration.
## Systems talk to each other through these signals instead of direct references.

# --- gameplay
signal coins_changed(total: int)
signal gems_changed(total: int)
signal player_health_changed(current: float, maximum: float)
signal player_energy_changed(current: float, maximum: float)
signal player_died
signal player_lives_changed(lives: int)
signal powerup_started(id: String, duration: float)
signal powerup_ended(id: String)
signal checkpoint_reached(index: int)
signal level_completed
signal enemy_killed(enemy: Node)
signal boss_health_changed(current: float, maximum: float)
signal boss_started(boss_name: String, title: String)
signal boss_defeated(boss_id: String)
signal ability_cooldown_changed(ratio: float)
signal level_coins_changed(collected: int, total: int)
signal toast(text: String, color: Color)
signal camera_shake(strength: float, duration: float)
signal hit_stop(duration: float)

# --- meta
signal currency_changed
signal settings_changed
signal controls_layout_changed

const ACTIONS := {
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"move_up": [KEY_W, KEY_UP],
	"move_down": [KEY_S, KEY_DOWN],
	"jump": [KEY_SPACE, KEY_K],
	"attack": [KEY_J, KEY_X],
	"special": [KEY_L, KEY_C],
	"ability": [KEY_I, KEY_V],
	"pause": [KEY_ESCAPE, KEY_P],
}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for action in ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.2)
		for key in ACTIONS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
