extends Node
## Music manager (cross-fading pair of players) + pooled SFX players.

const MUSIC_DIR := "res://assets/audio/music/"
const SFX_DIR := "res://assets/audio/sfx/"
const SFX_POOL_SIZE := 14
const UI_SOUNDS := ["click", "menu_accept", "menu_move", "menu_cancel", "pop", "error", "purchase", "unlock", "logo", "whoosh"]

var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _active: AudioStreamPlayer
var _current_track := ""
var _pool: Array[AudioStreamPlayer] = []
var _pool_index := 0
var _cache := {}
var _last_played := {}
var _music_tween: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_music_a = _make_player("Music")
	_music_b = _make_player("Music")
	_active = _music_a
	for i in SFX_POOL_SIZE:
		_pool.append(_make_player("SFX"))
	apply_volumes()
	Events.settings_changed.connect(apply_volumes)


func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func apply_volumes() -> void:
	_set_bus("Music", float(SaveManager.setting("music")))
	_set_bus("SFX", float(SaveManager.setting("sfx")))
	_set_bus("UI", float(SaveManager.setting("sfx")))


func _set_bus(bus_name: String, linear: float) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx < 0:
		return
	AudioServer.set_bus_volume_db(idx, linear_to_db(max(linear, 0.0001)))
	AudioServer.set_bus_mute(idx, linear <= 0.001)


func _load(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	var s: AudioStream = null
	if ResourceLoader.exists(path):
		s = load(path)
	_cache[path] = s
	return s


# ------------------------------------------------------------------ music
func play_music(track: String, fade := 1.0) -> void:
	if track == _current_track and _active.playing:
		return
	var stream := _load(MUSIC_DIR + track + ".ogg")
	if stream == null:
		return
	if stream is AudioStreamOggVorbis:
		stream.loop = true
	_current_track = track
	var old := _active
	_active = _music_b if _active == _music_a else _music_a
	_active.stream = stream
	_active.volume_db = -40.0
	_active.play()
	if _music_tween:
		_music_tween.kill()
	_music_tween = create_tween().set_parallel(true)
	_music_tween.tween_property(_active, "volume_db", 0.0, fade)
	if old.playing:
		_music_tween.tween_property(old, "volume_db", -40.0, fade)
		_music_tween.chain().tween_callback(old.stop)


func stop_music(fade := 0.8) -> void:
	_current_track = ""
	if _music_tween:
		_music_tween.kill()
	_music_tween = create_tween()
	_music_tween.tween_property(_active, "volume_db", -40.0, fade)
	_music_tween.tween_callback(_active.stop)


func duck_music(amount_db := -10.0, time := 0.3) -> void:
	var t := create_tween()
	t.tween_property(_active, "volume_db", amount_db, time)


func unduck_music(time := 0.6) -> void:
	var t := create_tween()
	t.tween_property(_active, "volume_db", 0.0, time)


# -------------------------------------------------------------------- sfx
func play_sfx(id: String, pitch_variation := 0.06, volume_db := 0.0) -> void:
	var now := Time.get_ticks_msec()
	if _last_played.get(id, -1000) > now - 35:
		return  # avoid stacking the identical sound in the same frame
	_last_played[id] = now
	var stream := _load(SFX_DIR + id + ".wav")
	if stream == null:
		stream = _load(SFX_DIR + id + ".ogg")
	if stream == null:
		return
	var p := _pool[_pool_index]
	_pool_index = (_pool_index + 1) % _pool.size()
	p.bus = "UI" if UI_SOUNDS.has(id) else "SFX"
	p.stream = stream
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_variation, pitch_variation)
	p.play()


func play_ui(id := "click") -> void:
	play_sfx(id, 0.0)
