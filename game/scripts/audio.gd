class_name GameAudio
extends Node
## Plays the recorded sounds (assets/downloaded/sounds/*.ogg). Missing files are simply silent.

const DIR := "res://assets/downloaded/sounds/"
var cache := {}
var loops := {}


func stream(n: String) -> AudioStream:
	if cache.has(n):
		return cache[n]
	var s: AudioStream = null
	var p := DIR + n + ".ogg"
	if ResourceLoader.exists(p):
		s = load(p)
	cache[n] = s
	return s


func has(n: String) -> bool:
	return stream(n) != null


func play(n: String, vol := 0.0, pitch := 1.0) -> void:
	var s := stream(n)
	if s == null:
		return
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = vol
	p.pitch_scale = pitch
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()


func play3d(n: String, pos: Vector3, vol := 0.0, pitch := 1.0) -> void:
	var s := stream(n)
	if s == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = vol
	p.pitch_scale = pitch
	p.unit_size = 5.0
	p.max_distance = 40.0
	add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()


func loop(n: String, vol := 0.0) -> void:
	if loops.has(n):
		loops[n].volume_db = vol
		if not loops[n].playing:
			loops[n].play()
		return
	var s := stream(n)
	if s == null:
		return
	if s is AudioStreamOggVorbis:
		s.loop = true
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = vol
	add_child(p)
	p.play()
	loops[n] = p


func stop(n: String) -> void:
	if loops.has(n):
		loops[n].stop()


func stop_all() -> void:
	for k in loops:
		loops[k].stop()
	for c in get_children():
		if c is AudioStreamPlayer3D or (c is AudioStreamPlayer and not loops.values().has(c)):
			c.queue_free()


func set_vol(n: String, vol: float) -> void:
	if loops.has(n):
		loops[n].volume_db = vol
