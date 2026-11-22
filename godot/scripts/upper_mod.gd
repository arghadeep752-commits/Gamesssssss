class_name UpperMod
extends SkeletonModifier3D
## Layers an upper-body clip (aiming, shooting) over whatever the legs are doing, after the AnimationPlayer.

const BONES := ["Spine", "Chest", "Neck", "Head", "Shoulder_R", "UpperArm_R", "LowerArm_R", "Hand_R",
	"Shoulder_L", "UpperArm_L", "LowerArm_L", "Hand_L"]

var anim: Animation
var t := 0.0
var weight := 0.0
var tracks := {}            # bone index -> rotation track index


func set_clip(a: Animation) -> void:
	if a == anim:
		return
	anim = a
	tracks.clear()
	var sk := get_skeleton()
	if a == null or sk == null:
		return
	for i in a.get_track_count():
		if a.track_get_type(i) != Animation.TYPE_ROTATION_3D:
			continue
		var bone := String(a.track_get_path(i).get_concatenated_subnames())
		if bone in BONES:
			var bi := sk.find_bone(bone)
			if bi >= 0:
				tracks[bi] = i


func _apply() -> void:
	if anim == null or weight <= 0.001:
		return
	var sk := get_skeleton()
	if sk == null:
		return
	var tt := fmod(t, maxf(0.01, anim.length)) if anim.loop_mode != Animation.LOOP_NONE else minf(t, anim.length)
	for b in tracks:
		var q := anim.rotation_track_interpolate(tracks[b], tt)
		sk.set_bone_pose_rotation(b, sk.get_bone_pose_rotation(b).slerp(q, weight))


func _process_modification_with_delta(_delta: float) -> void:
	_apply()


func _process_modification() -> void:
	_apply()
