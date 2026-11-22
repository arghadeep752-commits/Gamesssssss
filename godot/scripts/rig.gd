class_name Rig
extends Node3D
## A rigged character: its AnimationPlayer for the whole body (with cross-fades) and an upper-body layer.

var model := ""
var root: Node3D
var skeleton: Skeleton3D
var player: AnimationPlayer
var upper: UpperMod
var current := ""
var speed := 1.0
var update_every := 0.0          # seconds between animation updates far from the camera (0 = every frame)
var _acc := 0.0
var _upper_name := ""
var _upper_target := 0.0
var hand_r := Vector3.ZERO
var hand_tip_r := Vector3.ZERO


static func create(m: String, parent: Node3D) -> Rig:
	var r := Rig.new()
	r.name = "rig"
	parent.add_child(r)
	r.model = m
	r.root = G.game.models.character(m)
	if r.root == null:
		return r
	r.add_child(r.root)
	r.skeleton = r.root.find_child("*", true, false) as Skeleton3D
	if r.skeleton == null:
		for n in r.root.find_children("*", "Skeleton3D", true, false):
			r.skeleton = n
			break
	for n in r.root.find_children("*", "AnimationPlayer", true, false):
		r.player = n
		break
	if r.player:
		r.player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	if r.skeleton:
		r.upper = UpperMod.new()
		r.skeleton.add_child(r.upper)
	var info: Dictionary = G.game.models.characters.get(m, {}).get("points", {})
	r.hand_r = G.v3(info.get("hand_r"))
	r.hand_tip_r = G.v3(info.get("hand_tip_r"))
	r.play("idle", 0.0)
	return r


func has_clip(c: String) -> bool:
	return player != null and player.has_animation(c)


func play(c: String, fade := 0.2, spd := 1.0, restart := false) -> void:
	if player == null or not player.has_animation(c):
		return
	speed = spd
	if c == current and not restart:
		player.speed_scale = spd
		return
	current = c
	player.speed_scale = spd
	player.play(c, fade)
	if restart:
		player.seek(0.0, true)


func is_finished() -> bool:
	if player == null or current == "":
		return true
	var a := player.get_animation(current)
	if a == null or a.loop_mode != Animation.LOOP_NONE:
		return false
	return player.current_animation_position >= a.length - 0.02 or not player.is_playing()


## Upper-body clip ('' = none): aiming and shooting while the legs walk or run.
func set_upper(c: String, weight := 1.0) -> void:
	if upper == null:
		return
	if c == "":
		_upper_target = 0.0
		return
	if c != _upper_name:
		_upper_name = c
		upper.set_clip(player.get_animation(c) if player and player.has_animation(c) else null)
		upper.t = 0.0
	_upper_target = weight


func restart_upper() -> void:
	if upper:
		upper.t = 0.0


func bone_attachment(bone: String) -> BoneAttachment3D:
	if skeleton == null:
		return null
	var name := "att_" + bone
	var a := skeleton.get_node_or_null(name) as BoneAttachment3D
	if a == null:
		a = BoneAttachment3D.new()
		a.name = name
		a.bone_name = bone
		skeleton.add_child(a)
	return a


func _process(delta: float) -> void:
	if player == null:
		return
	_acc += delta
	if update_every > 0.0 and _acc < update_every:
		return
	var dt := _acc
	_acc = 0.0
	player.advance(dt)
	if upper:
		upper.weight = move_toward(upper.weight, _upper_target, dt * 6.0)
		upper.t += dt
