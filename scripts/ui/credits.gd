extends MenuScreen
## Scrolling credits.

const LINES := [
	["NINJA: SHADOW LEGACY", 56, Color(1, 0.86, 0.35)],
	["", 20, Color.WHITE],
	["A GAME BY", 26, Color(0.8, 0.8, 1)],
	["MXYAN GAMES", 52, Color.WHITE],
	["", 30, Color.WHITE],
	["ARTWORK", 30, Color(1, 0.86, 0.35)],
	["Ninja character & kunai", 26, Color(0.85, 0.85, 1)],
	["pzUH - GameArt2D.com (CC0)", 30, Color.WHITE],
	["Worlds, enemies, items, UI, controls, particles", 26, Color(0.85, 0.85, 1)],
	["Kenney - kenney.nl (CC0)", 30, Color.WHITE],
	["Weapons, projectiles, chest, effects", 26, Color(0.85, 0.85, 1)],
	["Pixel-boy & AAA - Ninja Adventure (CC0)", 30, Color.WHITE],
	["", 30, Color.WHITE],
	["MUSIC & SOUND", 30, Color(1, 0.86, 0.35)],
	["Music & sound effects", 26, Color(0.85, 0.85, 1)],
	["Ninja Adventure pack - Pixel-boy & AAA (CC0)", 30, Color.WHITE],
	["Sound effects & voice", 26, Color(0.85, 0.85, 1)],
	["Kenney audio packs (CC0)", 30, Color.WHITE],
	["", 30, Color.WHITE],
	["FONTS", 30, Color(1, 0.86, 0.35)],
	["Kenney Fonts (CC0)", 30, Color.WHITE],
	["", 30, Color.WHITE],
	["ENGINE", 30, Color(1, 0.86, 0.35)],
	["Made with Godot Engine (MIT licence)", 30, Color.WHITE],
	["godotengine.org/license", 24, Color(0.85, 0.85, 1)],
	["", 40, Color.WHITE],
	["Thank you for playing!", 40, Color(0.6, 1, 0.7)],
]

var _scroll: Control
var _speed := 70.0


func _ready() -> void:
	setup_screen("CREDITS", 6)
	AudioManager.play_music("credits", 1.0)
	var clip := Control.new()
	clip.clip_contents = true
	clip.size_flags_vertical = Control.SIZE_EXPAND_FILL
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	content.add_child(clip)
	_scroll = VBoxContainer.new()
	(_scroll as VBoxContainer).add_theme_constant_override("separation", 10)
	_scroll.position = Vector2(0, 900)
	_scroll.custom_minimum_size = Vector2(672, 0)
	clip.add_child(_scroll)
	for l in LINES:
		var lab := UITheme.make_label(l[0], l[1], l[2], true)
		lab.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lab.custom_minimum_size = Vector2(672, 0)
		_scroll.add_child(lab)


func _process(delta: float) -> void:
	super._process(delta)
	if _scroll:
		_scroll.position.y -= _speed * delta
		if _scroll.position.y < -_scroll.size.y - 50:
			_scroll.position.y = 900


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		_speed = 260.0 if event.pressed else 70.0


func _on_back_key() -> void:
	SceneManager.goto_menu("res://scenes/menus/main_menu.tscn")
