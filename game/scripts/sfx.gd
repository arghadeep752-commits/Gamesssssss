extends Node
## Sound effects. All recordings are real sounds downloaded at build time (see tools/fetch_sounds.py and
## CREDITS.md); a missing file is simply silent.

const DIR := "res://assets/sounds/"
const EXT := [".ogg", ".mp3", ".wav"]

var _cache := {}
var _variants := {}

func has(sound_name: String) -> bool:
	return get_stream(sound_name) != null

func get_stream(sound_name: String) -> AudioStream:
	if _cache.has(sound_name):
		return _cache[sound_name]
	var s: AudioStream = null
	for e in EXT:
		var p: String = DIR + sound_name + e
		if ResourceLoader.exists(p):
			s = load(p)
			break
	_cache[sound_name] = s
	return s

## Numbered variants: name_1, name_2, ... (or just name).
func get_variant(base: String) -> AudioStream:
	if not _variants.has(base):
		var list: Array = []
		var one := get_stream(base)
		if one:
			list.append(one)
		for i in range(1, 10):
			var v := get_stream("%s_%d" % [base, i])
			if v:
				list.append(v)
		_variants[base] = list
	var l: Array = _variants[base]
	if l.is_empty():
		return null
	return l[randi() % l.size()]

func make_loop(stream: AudioStream) -> AudioStream:
	if stream == null:
		return null
	var s: AudioStream = stream.duplicate()
	if s is AudioStreamOggVorbis:
		s.loop = true
	elif s is AudioStreamMP3:
		s.loop = true
	elif s is AudioStreamWAV:
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_end = int(s.get_length() * s.mix_rate)
	return s

## One-shot, non-positional sound.
func play(sound_name: String, volume_db := 0.0, pitch := 1.0) -> AudioStreamPlayer:
	var s := get_variant(sound_name)
	if s == null:
		return null
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = pitch
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()
	return p

## One-shot positional sound that lives in the world.
func play_at(sound_name: String, parent: Node, pos: Vector3, volume_db := 0.0, pitch := 1.0, max_dist := 22.0) -> AudioStreamPlayer3D:
	var s := get_variant(sound_name)
	if s == null:
		return null
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = pitch
	p.max_distance = max_dist
	p.unit_size = 4.0
	parent.add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()
	return p

## Looping player attached to a node.
func loop_on(sound_name: String, parent: Node, volume_db := 0.0, positional := false, max_dist := 20.0) -> Node:
	var s := make_loop(get_stream(sound_name))
	if s == null:
		return null
	var p: Node
	if positional:
		var p3 := AudioStreamPlayer3D.new()
		p3.max_distance = max_dist
		p3.unit_size = 3.0
		p3.volume_db = volume_db
		p3.stream = s
		p = p3
	else:
		var p2 := AudioStreamPlayer.new()
		p2.volume_db = volume_db
		p2.stream = s
		p = p2
	parent.add_child(p)
	p.play()
	return p
