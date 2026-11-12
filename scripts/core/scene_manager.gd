extends CanvasLayer
## Scene transitions with fade + a lightweight loading screen for gameplay scenes.

const GAME_SCENE := "res://scenes/gameplay/game.tscn"

var params := {}
var _fade: ColorRect
var _loading: Control
var _bar: TextureProgressBar
var _tip: Label
var _busy := false

const TIPS := [
	"Tip: Jump on slimes to defeat them, but never on spiked ones!",
	"Tip: Checkpoint flags save your progress inside a level.",
	"Tip: Breakable crates often hide gems and hearts.",
	"Tip: Your special attack charges as you land hits.",
	"Tip: Upgrade weapons in the Inventory to deal more damage.",
	"Tip: Bosses flash before a big attack - watch for the warning!",
	"Tip: Some walls look solid but hide secret rooms.",
	"Tip: Drag the controls to new positions in Settings.",
]


func _ready() -> void:
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fade)
	_build_loading()


func _build_loading() -> void:
	_loading = Control.new()
	_loading.set_anchors_preset(Control.PRESET_FULL_RECT)
	_loading.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_loading.visible = false
	add_child(_loading)
	var box := VBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	box.position = Vector2(-260, -260)
	box.size = Vector2(520, 160)
	box.add_theme_constant_override("separation", 18)
	_loading.add_child(box)
	var title := Label.new()
	title.text = "LOADING"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_override("font", UITheme.font_bold)
	title.add_theme_font_size_override("font_size", 40)
	box.add_child(title)
	_bar = UITheme.make_progress("blue", Vector2(520, 44))
	box.add_child(_bar)
	_tip = Label.new()
	_tip.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tip.custom_minimum_size = Vector2(520, 60)
	_tip.add_theme_font_size_override("font_size", 22)
	_tip.modulate = Color(1, 1, 1, 0.8)
	box.add_child(_tip)


func change_scene(path: String, new_params := {}, fade_time := 0.35) -> void:
	if _busy:
		return
	_busy = true
	params = new_params
	get_tree().paused = false
	_fade.mouse_filter = Control.MOUSE_FILTER_STOP
	var t := create_tween()
	t.tween_property(_fade, "color:a", 1.0, fade_time)
	await t.finished
	if path == GAME_SCENE:
		await _threaded_load(path)
	else:
		get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	var t2 := create_tween()
	t2.tween_property(_fade, "color:a", 0.0, fade_time)
	await t2.finished
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_busy = false


func _threaded_load(path: String) -> void:
	_loading.visible = true
	_tip.text = TIPS[randi() % TIPS.size()]
	_bar.value = 0
	ResourceLoader.load_threaded_request(path)
	var progress := []
	var shown := 0.0
	while true:
		var status := ResourceLoader.load_threaded_get_status(path, progress)
		if status == ResourceLoader.THREAD_LOAD_LOADED:
			break
		if status == ResourceLoader.THREAD_LOAD_FAILED or status == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			push_error("Failed to load " + path)
			break
		shown = max(shown, float(progress[0]) * 100.0 if progress.size() > 0 else shown)
		_bar.value = shown
		await get_tree().process_frame
	var packed: PackedScene = ResourceLoader.load_threaded_get(path)
	_bar.value = 100
	await get_tree().create_timer(0.15).timeout
	get_tree().change_scene_to_packed(packed)
	_loading.visible = false


func start_level(index: int, from_checkpoint := true) -> void:
	SaveManager.data.last_level = index
	SaveManager.mark_dirty()
	change_scene(GAME_SCENE, {"level": index, "from_checkpoint": from_checkpoint})


func goto_menu(path: String, new_params := {}) -> void:
	change_scene(path, new_params, 0.25)
