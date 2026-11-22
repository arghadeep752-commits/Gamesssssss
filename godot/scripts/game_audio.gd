class_name GameAudio
extends Node
## Recorded sound effects (3D one-shots and loops), ambience by place and time, the radio, the menu music.

const STATIONS := ["radio_desi", "radio_hiphop", "radio_sitar", "music_chase"]
const STATION_NAMES := ["Agartala FM - Desi", "Tripura Beats - Hip Hop", "Raag Radio - Sitar", "Chase FM"]

var clips := {}
var pool: Array[AudioStreamPlayer3D] = []
var ui_player: AudioStreamPlayer
var amb_a: AudioStreamPlayer
var amb_b: AudioStreamPlayer
var radio: AudioStreamPlayer
var amb_name := ""
var sfx := 1.0
var music := 0.7
var station := 0
var next_amb := 0.0
var menu_track := false
var _amb_a_vol := 0.0
var _amb_b_vol := 0.0


static func create(parent: Node) -> GameAudio:
	var a := GameAudio.new()
	a.name = "audio"
	a.process_mode = Node.PROCESS_MODE_ALWAYS
	parent.add_child(a)
	a.ui_player = AudioStreamPlayer.new()
	a.add_child(a.ui_player)
	a.amb_a = AudioStreamPlayer.new()
	a.amb_b = AudioStreamPlayer.new()
	a.add_child(a.amb_a)
	a.add_child(a.amb_b)
	a.radio = AudioStreamPlayer.new()
	a.add_child(a.radio)
	G.audio = a
	return a


func clip(name: String) -> AudioStream:
	if clips.has(name):
		return clips[name]
	var c: AudioStream = null
	for dir in ["res://gen/sounds/", "res://gen/music/"]:
		var p: String = dir + name + ".ogg"
		if ResourceLoader.exists(p):
			c = load(p)
			break
	if c is AudioStreamOggVorbis:
		c = c.duplicate()
		c.loop = false
	clips[name] = c
	return c


func _looped(name: String) -> AudioStream:
	var key := name + "#loop"
	if clips.has(key):
		return clips[key]
	var c := clip(name)
	if c is AudioStreamOggVorbis:
		c = c.duplicate()
		c.loop = true
	clips[key] = c
	return c


func ui(name: String, vol := 1.0) -> void:
	var c := clip(name)
	if c == null:
		return
	ui_player.stream = c
	ui_player.volume_db = linear_to_db(maxf(0.001, vol * sfx))
	ui_player.play()


func at(name: String, p: Vector3, vol := 1.0, pitch := 1.0, min_dist := 5.0) -> void:
	var c := clip(name)
	if c == null:
		return
	if G.cam and G.cam.cam.global_position.distance_squared_to(p) > 160.0 * 160.0:
		return
	var s: AudioStreamPlayer3D = null
	for a in pool:
		if not a.playing:
			s = a
			break
	if s == null:
		if pool.size() >= 20:
			return
		s = AudioStreamPlayer3D.new()
		s.attenuation_model = AudioStreamPlayer3D.ATTENUATION_LOGARITHMIC
		s.doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_DISABLED
		s.max_distance = 200.0
		add_child(s)
		pool.append(s)
	s.global_position = p
	s.stream = c
	s.unit_size = min_dist
	s.pitch_scale = pitch
	s.volume_db = linear_to_db(maxf(0.001, vol * sfx))
	s.play()
	if c.get_length() > 6.0:
		var t := get_tree().create_timer(4.0, true)
		t.timeout.connect(func():
			if is_instance_valid(s) and s.stream == c:
				s.stop())


func loop(name: String, parent: Node3D) -> AudioStreamPlayer3D:
	var c := _looped(name)
	if c == null:
		return null
	var s := AudioStreamPlayer3D.new()
	s.stream = c
	s.unit_size = 6.0
	s.max_distance = 120.0
	s.attenuation_model = AudioStreamPlayer3D.ATTENUATION_LOGARITHMIC
	s.volume_db = -60.0
	parent.add_child(s)
	s.play(randf() * maxf(0.1, c.get_length() - 0.1))
	return s


func radio_on(on: bool) -> void:
	menu_track = false
	if not on or station < 0:
		radio.stop()
		return
	var c := _looped(STATIONS[station % STATIONS.size()])
	if c == null:
		return
	if radio.stream != c or not radio.playing:
		radio.stream = c
		radio.play(randf() * maxf(0.0, c.get_length() - 5.0))


func menu(on: bool) -> void:
	if on:
		var c := _looped("music_menu")
		if c and (radio.stream != c or not radio.playing):
			radio.stream = c
			radio.play(0.0)
		menu_track = true
	elif menu_track:
		radio.stop()
		menu_track = false


func _process(delta: float) -> void:
	radio.volume_db = linear_to_db(maxf(0.001, music * (0.28 if menu_track else 0.55)))
	var now := Time.get_ticks_msec() / 1000.0
	if now >= next_amb:
		next_amb = now + 1.0
		var want := "amb_city"
		var p := Player.I
		if p and G.city and p.active:
			var pos := p.global_position
			var zone: String = G.city.zone_at(pos)
			if G.env.night > 0.6:
				want = "amb_night"
			elif "Bazar" in zone or "Battala" in zone or "Chowmuhani" in zone or "Market" in zone:
				want = "amb_market"
			elif "Park" in zone or "Kanan" in zone or "Garden" in zone or "Palace" in zone:
				want = "amb_birds"
			var wl: float = G.city.water_level(pos.x, pos.z)
			if not is_nan(wl) and wl <= -0.9 and pos.z > 480.0:
				want = "amb_sea"
			if p.vehicle and p.vehicle.is_heli() and pos.y > 30.0:
				want = "amb_wind"
		if want != amb_name:
			amb_name = want
			var tmp := amb_a
			amb_a = amb_b
			amb_b = tmp
			var tv := _amb_a_vol
			_amb_a_vol = _amb_b_vol
			_amb_b_vol = tv
			var c := _looped(want)
			if c:
				amb_a.stream = c
				amb_a.play(randf() * maxf(0.0, c.get_length() - 2.0))
	var target := (0.15 if G.game and G.game.state == G.game.S.MENU else 0.35) * sfx
	_amb_a_vol = move_toward(_amb_a_vol, target, delta * 0.3)
	_amb_b_vol = move_toward(_amb_b_vol, 0.0, delta * 0.3)
	amb_a.volume_db = linear_to_db(maxf(0.001, _amb_a_vol))
	amb_b.volume_db = linear_to_db(maxf(0.001, _amb_b_vol))
	if _amb_b_vol <= 0.0 and amb_b.playing:
		amb_b.stop()
