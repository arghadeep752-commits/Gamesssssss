extends CharacterBody3D
## Chaya - the restless soul of a young wife, wandering her old wooden house in a torn red bridal saree.
## The body is a realistic rigged woman (Microsoft Rocketbox, MIT) with real motion capture animations;
## the saree skirt, her ashen skin and glowing eyes are added here.

signal caught_player

enum S { PATROL, HEARD, CHASE, SEARCH, IDLE, RITUAL }

const MODEL := "res://assets/downloaded/chaya/Medical_Female_01.fbx"
const ANIMS := {"walk": "walk", "run": "run", "idle": "idle"}
const WALK_SPEED := 1.25
const RUN_SPEED := 2.95
const ANIM_WALK_SPEED := 1.15
const ANIM_RUN_SPEED := 2.66
const MODEL_SCALE := 0.94

const BODY_SHADER := """
shader_type spatial;
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform vec3 saree : source_color = vec3(0.30, 0.008, 0.02);
uniform vec3 pallor : source_color = vec3(0.62, 0.70, 0.82);
uniform int mode = 0;
uniform float dissolve = 0.0;
uniform float rim_power = 2.6;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
void fragment() {
	vec3 c = texture(albedo_tex, UV).rgb;
	float mx = max(c.r, max(c.g, c.b));
	float mn = min(c.r, min(c.g, c.b));
	float sat = mx - mn;
	float lum = dot(c, vec3(0.299, 0.587, 0.114));
	vec3 skin = mix(vec3(lum), c, 0.5) * pallor * 0.85;
	vec3 col;
	float rough = 0.7;
	if (mode == 1) {
		float gold = step(0.5, c.r) * step(0.38, c.g) * step(c.b, 0.3);
		skin = mix(skin, vec3(0.015), gold);
		float d1 = length((UV - vec2(0.430, 0.283)) / vec2(0.062, 0.036));
		float d2 = length((UV - vec2(0.570, 0.283)) / vec2(0.062, 0.036));
		float sock = 1.0 - smoothstep(0.45, 1.3, min(d1, d2));
		skin *= mix(1.0, 0.10, sock);
		float tx = min(abs(UV.x - 0.428) + 0.006 * sin(UV.y * 190.0), abs(UV.x - 0.572) + 0.006 * sin(UV.y * 170.0 + 2.0));
		float tr = smoothstep(0.010, 0.002, tx) * smoothstep(0.30, 0.335, UV.y) * (1.0 - smoothstep(0.36, 0.50, UV.y));
		skin = mix(skin, vec3(0.30, 0.0, 0.0), tr * 0.95);
		float lip = 1.0 - smoothstep(0.5, 1.2, length((UV - vec2(0.5, 0.412)) / vec2(0.055, 0.016)));
		skin = mix(skin, vec3(0.10, 0.04, 0.07), lip * 0.8);
		col = skin;
		rough = 0.55;
	} else {
		float coat = smoothstep(0.26, 0.10, sat) * smoothstep(0.30, 0.55, mx);
		float grime = vnoise(UV * 22.0) * 0.6 + vnoise(UV * 61.0) * 0.4;
		vec3 cloth = saree * (0.35 + 0.9 * lum) * mix(1.0, 0.35, smoothstep(0.5, 0.85, grime));
		col = mix(skin, cloth, coat);
		rough = mix(0.62, 0.9, coat);
	}
	ALBEDO = col;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
	ROUGHNESS = rough;
	SPECULAR = 0.3;
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), rim_power);
	EMISSION = vec3(0.30, 0.01, 0.01) * f;
	if (dissolve > 0.0) {
		float n = vnoise(UV * 38.0) * 0.6 + vnoise(UV * 90.0) * 0.4;
		if (n < dissolve) discard;
		EMISSION += vec3(1.0, 0.55, 0.15) * (1.0 - smoothstep(dissolve, dissolve + 0.07, n)) * 3.0;
	}
}
"""

const CLOTH_SHADER := """
shader_type spatial;
render_mode cull_disabled;
uniform float dissolve = 0.0;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
void fragment() {
	float weave = 0.9 + 0.1 * sin(UV.x * 900.0) * sin(UV.y * 700.0);
	float stain = vnoise(UV * vec2(18.0, 7.0));
	vec3 base = COLOR.rgb * weave;
	base = mix(base, base * vec3(0.35, 0.25, 0.25), smoothstep(0.55, 0.9, stain) * 0.7);
	ALBEDO = base;
	ROUGHNESS = 0.85;
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.6);
	EMISSION = vec3(0.3, 0.01, 0.01) * f;
	if (dissolve > 0.0) {
		float n = vnoise(UV * vec2(30.0, 12.0)) * 0.6 + vnoise(UV * vec2(90.0, 40.0)) * 0.4;
		if (n < dissolve) discard;
		EMISSION += vec3(1.0, 0.55, 0.15) * (1.0 - smoothstep(dissolve, dissolve + 0.07, n)) * 3.0;
	}
}
"""

var level
var maze: MazeData
var player: CharacterBody3D
var state := S.PATROL
var enraged := false
var visual: Node3D
var skel: Skeleton3D
var anim: AnimationPlayer
var skirt: MeshInstance3D
var _pelvis := -1
var _path := PackedVector3Array()
var _path_i := 0
var _target := Vector3.ZERO
var _wait := 0.0
var _last_seen := Vector3.ZERO
var _lost := 0.0
var _repath := 0.0
var _anim_name := ""
var _step_t := 0.0
var _stuck_t := 0.0
var _last_pos := Vector3.ZERO
var _hunt_t := 8.0
var _body_mats: Array = []
var _cloth_mat: ShaderMaterial
var _whisper: Node
var _yaw := 0.0
var _eye_glow: Array = []
var hair_root: Node3D
var _head := -1
var _hair_mat: StandardMaterial3D
var active := true

func setup(lvl, m: MazeData, p: CharacterBody3D) -> void:
	level = lvl
	maze = m
	player = p
	collision_layer = 4
	collision_mask = 1
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.7
	col.shape = cap
	col.position.y = 0.85
	add_child(col)
	_build_visual()
	_whisper = Sfx.loop_on("ghost_whisper", self, -3.0, true, 16.0)
	state = S.PATROL
	_pick_patrol_target()

# ------------------------------------------------------------------------------------------ visuals

func _retarget(clip: Animation, sk: Skeleton3D) -> Animation:
	var a := clip.duplicate() as Animation
	a.loop_mode = Animation.LOOP_LINEAR
	for t in range(a.get_track_count() - 1, -1, -1):
		var path := str(a.track_get_path(t))
		if not path.begins_with("Skeleton3D:"):
			a.remove_track(t)
			continue
		var bone := path.substr(11)
		if sk.find_bone(bone) < 0:
			a.remove_track(t)
			continue
		if a.track_get_type(t) == Animation.TYPE_POSITION_3D:
			if bone != "Bip01":
				a.remove_track(t)
			else:   # keep the up/down sway, drop the forward travel (the game moves her)
				for k in range(a.track_get_key_count(t)):
					var v: Vector3 = a.track_get_key_value(t, k)
					a.track_set_key_value(t, k, Vector3(v.x, v.y, 0.0))
	return a

func _build_visual() -> void:
	visual = Node3D.new()
	visual.rotation.y = PI
	visual.scale = Vector3.ONE * MODEL_SCALE
	add_child(visual)
	var ps: PackedScene = load(MODEL)
	if ps == null:
		push_warning("Chaya model missing")
		return
	var model: Node3D = ps.instantiate()
	visual.add_child(model)
	skel = model.get_node("Skeleton3D") as Skeleton3D
	_pelvis = skel.find_bone("Bip01 Pelvis")
	anim = model.get_node("AnimationPlayer") as AnimationPlayer
	var lib := AnimationLibrary.new()
	for key in ANIMS:
		var p: PackedScene = load("res://assets/downloaded/chaya/anims/%s.fbx" % ANIMS[key])
		if p == null:
			continue
		var inst := p.instantiate()
		var found := inst.find_children("*", "AnimationPlayer", true, false)
		if found.size() > 0:
			var src := found[0] as AnimationPlayer
			var names := src.get_animation_list()
			if names.size() > 0:
				lib.add_animation(key, _retarget(src.get_animation(names[0]), skel))
		inst.free()
	anim.add_animation_library("c", lib)
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	for mn in meshes:
		var mi := mn as MeshInstance3D
		for i in range(mi.mesh.get_surface_count()):
			var orig = mi.mesh.surface_get_material(i)
			var tex_a: Texture2D = null
			var tex_n: Texture2D = null
			if orig is BaseMaterial3D:
				tex_a = (orig as BaseMaterial3D).albedo_texture
				tex_n = (orig as BaseMaterial3D).normal_texture
			if i == 2:      # hair strands / lashes: keep the alpha texture, make it black
				var h := (orig as BaseMaterial3D).duplicate() as BaseMaterial3D
				h.albedo_color = Color(0.1, 0.09, 0.09)
				mi.set_surface_override_material(i, h)
				continue
			var sm := ShaderMaterial.new()
			var sh := Shader.new()
			sh.code = BODY_SHADER
			sm.shader = sh
			sm.set_shader_parameter("albedo_tex", tex_a)
			sm.set_shader_parameter("normal_tex", tex_n)
			sm.set_shader_parameter("mode", 1 if i == 1 else 0)
			mi.set_surface_override_material(i, sm)
			_body_mats.append(sm)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	# saree skirt
	skirt = _make_skirt()
	visual.add_child(skirt)
	# long black hair
	_head = skel.find_bone("Bip01 Head")
	hair_root = Node3D.new()
	visual.add_child(hair_root)
	hair_root.add_child(_make_hair())
	# glowing red eyes
	for bn in ["Bip01 REye", "Bip01 LEye"]:
		var bi := skel.find_bone(bn)
		if bi < 0:
			continue
		var att := BoneAttachment3D.new()
		att.bone_name = bn
		skel.add_child(att)
		var mesh := MeshInstance3D.new()
		var sp := SphereMesh.new()
		sp.radius = 0.0125
		sp.height = 0.025
		sp.radial_segments = 10
		sp.rings = 6
		mesh.mesh = sp
		var em := StandardMaterial3D.new()
		em.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		em.albedo_color = Color(1.0, 0.05, 0.02)
		mesh.material_override = em
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		att.add_child(mesh)
		_eye_glow.append(mesh)
	_play("idle")

func _make_skirt() -> MeshInstance3D:
	var seg := 30
	var rings := 10
	var verts := PackedVector3Array()
	var cols := PackedColorArray()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	for r in range(rings + 1):
		var t := float(r) / rings
		var rad := lerpf(0.185, 0.50, pow(t, 0.75))
		for s in range(seg + 1):
			var a := TAU * float(s) / seg
			var rip := 1.0 + 0.09 * t * sin(a * 7.0 + t * 2.5) + 0.05 * t * sin(a * 13.0 + 1.3)
			var y := -t
			if r == rings:
				y -= (0.5 + 0.5 * sin(a * 9.0 + 0.7) * sin(a * 4.0)) * 0.05   # torn hem
			verts.append(Vector3(cos(a) * rad * rip, y, sin(a) * rad * rip))
			var c := Color(0.52, 0.012, 0.03)
			if t > 0.80 and t < 0.93:
				c = Color(0.86, 0.62, 0.14)      # gold border
			elif t >= 0.93:
				c = Color(0.38, 0.01, 0.02)
			cols.append(c)
			uvs.append(Vector2(float(s) / seg, t))
	for r in range(rings):
		for s in range(seg):
			var a0 := r * (seg + 1) + s
			var b0 := a0 + 1
			var c0 := a0 + seg + 1
			var d0 := c0 + 1
			idx.append_array([a0, b0, c0, b0, d0, c0])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var st := SurfaceTool.new()
	var tmp := ArrayMesh.new()
	tmp.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	st.create_from(tmp, 0)
	st.generate_normals()
	var mesh := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var sh := Shader.new()
	sh.code = CLOTH_SHADER
	_cloth_mat = ShaderMaterial.new()
	_cloth_mat.shader = sh
	mi.material_override = _cloth_mat
	return mi

func _hair_texture() -> ImageTexture:
	var w := 256
	var h := 512
	var data := PackedByteArray()
	data.resize(w * h * 4)
	var rng := RandomNumberGenerator.new()
	rng.seed = 77
	var length := PackedFloat32Array()
	var shade := PackedFloat32Array()
	for x in range(w):
		if x % 3 == 0:
			length.append(rng.randf_range(0.62, 1.0))
			shade.append(rng.randf_range(0.0, 1.0))
		else:
			length.append(length[x - 1] + rng.randf_range(-0.03, 0.03))
			shade.append(shade[x - 1])
	for y in range(h):
		var v := float(y) / h
		for x in range(w):
			var u := float(x) / w
			var l := length[x]
			var a := clampf((l - v) * 14.0, 0.0, 1.0)
			# the face gap in front (u = 0.5 is straight ahead), closing below the chin
			var gap := 1.0 - smoothstep(0.045, 0.085, absf(u - 0.5)) * 0.0
			var du := minf(u, 1.0 - u)
			if du < 0.075 + 0.02 * sin(v * 40.0 + u * 90.0) and v > 0.10 and v < 0.40:
				a = 0.0
			if rng.randf() < 0.05 + v * 0.18:
				a *= 0.0
			var g := 0.02 + 0.05 * shade[x] * (0.6 + 0.4 * sin(v * 60.0 + shade[x] * 9.0))
			var i := (y * w + x) * 4
			data[i] = int(g * 255.0)
			data[i + 1] = int(g * 0.95 * 255.0)
			data[i + 2] = int(g * 0.9 * 255.0)
			data[i + 3] = int(a * 255.0)
	var img := Image.create_from_data(w, h, true, Image.FORMAT_RGBA8, data) if false else Image.create_from_data(w, h, false, Image.FORMAT_RGBA8, data)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)

func _make_hair() -> MeshInstance3D:
	var seg := 40
	var rows := 22
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	var top := 0.25
	var bottom := -0.78
	for r in range(rows + 1):
		var t := float(r) / rows
		var y := lerpf(top, bottom, t)
		# radii: lateral, front, back (metres, model space; +z is forward)
		var rx := 0.0
		var rzf := 0.0
		var rzb := 0.0
		if y > 0.12:
			var k := clampf((top - y) / (top - 0.12), 0.0, 1.0)
			var sh := sqrt(1.0 - (1.0 - k) * (1.0 - k))
			rx = lerpf(0.0, 0.112, sh)
			rzf = lerpf(0.0, 0.128, sh)
			rzb = lerpf(0.0, 0.125, sh)
		elif y > 0.0:
			rx = 0.112
			rzf = 0.128
			rzb = 0.125
		else:
			var k2 := clampf(-y / 0.18, 0.0, 1.0)
			var s2 := k2 * k2 * (3.0 - 2.0 * k2)
			rx = lerpf(0.112, 0.205, s2)
			rzf = lerpf(0.128, 0.165, s2)
			rzb = lerpf(0.125, 0.135, s2)
			if y < -0.35:
				var k3 := clampf((-y - 0.35) / 0.43, 0.0, 1.0)
				rx = lerpf(rx, 0.17, k3)
		for sidx in range(seg + 1):
			var phi := TAU * float(sidx) / seg           # 0 = straight ahead
			var wave := 1.0 + 0.04 * sin(phi * 9.0 + t * 7.0)
			var sn := sin(phi)
			var cs := cos(phi)
			var rz := rzf if cs >= 0.0 else rzb
			verts.append(Vector3(sn * rx * wave, y, cs * rz * wave))
			uvs.append(Vector2(float(sidx) / seg, t))
	for r in range(rows):
		for sidx in range(seg):
			var a := r * (seg + 1) + sidx
			var b := a + 1
			var c := a + seg + 1
			var d := c + 1
			idx.append_array([a, c, b, b, c, d])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var tmp := ArrayMesh.new()
	tmp.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var st := SurfaceTool.new()
	st.create_from(tmp, 0)
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	_hair_mat = StandardMaterial3D.new()
	_hair_mat.albedo_texture = _hair_texture()
	_hair_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	_hair_mat.alpha_scissor_threshold = 0.5
	_hair_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_hair_mat.roughness = 0.9
	_hair_mat.metallic_specular = 0.12
	mi.material_override = _hair_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi

func _play(clip: String, speed := 1.0) -> void:
	if anim == null:
		return
	if _anim_name != clip:
		_anim_name = clip
		if anim.has_animation("c/" + clip):
			anim.play("c/" + clip, 0.35)
	anim.speed_scale = speed

func set_dissolve(v: float) -> void:
	for m in _body_mats:
		(m as ShaderMaterial).set_shader_parameter("dissolve", v)
	if _cloth_mat:
		_cloth_mat.set_shader_parameter("dissolve", v)
	if v > 0.0 and v < 1.0:
		for e in _eye_glow:
			(e as Node3D).visible = false

func show_only() -> void:
	_build_visual()


func enrage() -> void:
	enraged = true

# ------------------------------------------------------------------------------------------ AI

func _eye_pos() -> Vector3:
	return global_position + Vector3(0, 1.5, 0)

func _can_see_player() -> bool:
	var to := player.global_position + Vector3(0, 1.3, 0) - _eye_pos()
	var dist := to.length()
	if dist > (20.0 if enraged else 15.0):
		return false
	var fwd := -global_transform.basis.z
	var flat := Vector3(to.x, 0, to.z).normalized()
	if dist > 2.2 and fwd.dot(flat) < 0.25:
		return false
	var q := PhysicsRayQueryParameters3D.create(_eye_pos(), player.global_position + Vector3(0, 1.3, 0), 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.is_empty()

func _hears_player() -> bool:
	var n: float = player.noise
	if n <= 0.0:
		return false
	var d := global_position.distance_to(player.global_position)
	var radius := (12.0 if n > 0.8 else 4.2) * (1.35 if enraged else 1.0)
	return d < radius

func _pick_patrol_target() -> void:
	var cells: Array = maze.open_cells
	var here := maze.world_to_cell(global_position)
	for _i in range(12):
		var c: Vector2i = cells[randi() % cells.size()]
		if abs(c.x - here.x) + abs(c.y - here.y) >= 5:
			_set_target(maze.cell_center(c))
			return
	_set_target(maze.cell_center(cells[randi() % cells.size()]))

func _set_target(p: Vector3) -> void:
	_target = p
	_path = maze.path(global_position, p)
	_path_i = 0
	_stuck_t = 0.0

func _follow_path(speed: float, dt: float, direct_to: Vector3 = Vector3.INF) -> bool:
	## returns true when the end of the path was reached
	var goal: Vector3
	var done := false
	if direct_to != Vector3.INF:
		goal = direct_to
	else:
		while _path_i < _path.size() and Vector2(global_position.x - _path[_path_i].x, global_position.z - _path[_path_i].z).length() < 0.55:
			_path_i += 1
		if _path_i >= _path.size():
			done = true
			goal = _target
		else:
			goal = _path[_path_i]
	var d := goal - global_position
	d.y = 0.0
	var dist := d.length()
	if dist < 0.35 and direct_to == Vector3.INF and done:
		velocity.x = 0.0
		velocity.z = 0.0
		return true
	var dir := d / maxf(dist, 0.001)
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	_yaw = lerp_angle(_yaw, atan2(-dir.x, -dir.z), clampf(dt * 7.0, 0.0, 1.0))
	rotation.y = _yaw
	return done

func _process(_dt: float) -> void:
	if skel == null:
		return
	if _pelvis >= 0 and skirt:
		var pw := skel.global_transform * skel.get_bone_global_pose(_pelvis).origin
		var top := pw.y + 0.07
		var hem := global_position.y + 0.02
		skirt.global_position = Vector3(visual.global_position.x, top, visual.global_position.z)
		skirt.scale = Vector3(1.0, maxf(0.2, top - hem), 1.0)
	if _head >= 0 and hair_root:
		hair_root.global_position = skel.global_transform * skel.get_bone_global_pose(_head).origin
		hair_root.global_basis = visual.global_basis

func _physics_process(dt: float) -> void:
	if not active or player == null:
		return
	velocity.y = 0.0 if is_on_floor() else velocity.y - 18.0 * dt
	var dist_p := global_position.distance_to(player.global_position)
	var sees := state != S.RITUAL and _can_see_player()
	match state:
		S.PATROL, S.IDLE:
			if sees:
				_enter_chase()
			elif _hears_player():
				state = S.HEARD
				_set_target(player.global_position)
			elif state == S.IDLE:
				velocity.x = 0.0
				velocity.z = 0.0
				_play("idle")
				_wait -= dt
				if _wait <= 0.0:
					state = S.PATROL
					_pick_patrol_target()
			else:
				var sp := WALK_SPEED * (1.2 if enraged else 1.0)
				_play("walk", sp / ANIM_WALK_SPEED)
				if _follow_path(sp, dt):
					state = S.IDLE
					_wait = randf_range(1.2, 3.2)
				if enraged:
					_hunt_t -= dt
					if _hunt_t <= 0.0:
						_hunt_t = 14.0
						state = S.HEARD
						_set_target(player.global_position)
		S.HEARD:
			if sees:
				_enter_chase()
			else:
				var sp2 := WALK_SPEED * 1.7
				_play("walk", sp2 / ANIM_WALK_SPEED)
				if _follow_path(sp2, dt):
					state = S.SEARCH
					_wait = randf_range(2.5, 4.5)
		S.CHASE:
			var sp3 := RUN_SPEED * (1.1 if enraged else 1.0)
			_play("run", sp3 / ANIM_RUN_SPEED)
			if sees:
				_last_seen = player.global_position
				_lost = 0.0
				_repath -= dt
				if dist_p < 3.5 or _line_clear_to(player.global_position):
					_follow_path(sp3, dt, player.global_position)
				else:
					if _repath <= 0.0:
						_repath = 0.35
						_set_target(player.global_position)
					_follow_path(sp3, dt)
			else:
				_lost += dt
				_repath -= dt
				if _repath <= 0.0:
					_repath = 0.5
					_set_target(_last_seen if _lost > 2.5 else player.global_position)
				var reached := _follow_path(sp3, dt)
				if _lost > 7.0 or (reached and _lost > 2.5):
					state = S.SEARCH
					_wait = randf_range(3.0, 5.0)
			if dist_p < 0.95 and not level.is_busy():
				active = false
				velocity = Vector3.ZERO
				caught_player.emit()
		S.SEARCH:
			velocity.x = 0.0
			velocity.z = 0.0
			_play("idle")
			_yaw += dt * 0.6
			rotation.y = _yaw
			_wait -= dt
			if sees:
				_enter_chase()
			elif _wait <= 0.0:
				state = S.PATROL
				_pick_patrol_target()
		S.RITUAL:
			_follow_path(RUN_SPEED * 0.45, dt, player.global_position)
			_play("walk", 0.7)
	move_and_slide()
	# stuck detection
	if state in [S.PATROL, S.HEARD, S.CHASE]:
		if global_position.distance_to(_last_pos) < 0.2 * dt:
			_stuck_t += dt
		else:
			_stuck_t = 0.0
		if _stuck_t > 1.8:
			_stuck_t = 0.0
			if state == S.PATROL:
				_pick_patrol_target()
			else:
				_set_target(player.global_position)
	_last_pos = global_position
	# footsteps
	var sp_now := Vector2(velocity.x, velocity.z).length()
	if sp_now > 0.4:
		_step_t -= dt
		if _step_t <= 0.0:
			_step_t = 0.62 if sp_now < 2.0 else 0.4
			Sfx.play_at("footstep", self, global_position, -1.0 if sp_now < 2.0 else 2.0, randf_range(0.7, 0.85), 24.0)

func _line_clear_to(p: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3(0, 0.8, 0), p + Vector3(0, 0.8, 0), 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()

func _enter_chase() -> void:
	if state != S.CHASE:
		state = S.CHASE
		_lost = 0.0
		_repath = 0.0
		level.ghost_spotted()

func start_ritual_mode() -> void:
	state = S.RITUAL
	collision_mask = 0

func warp_to(p: Vector3) -> void:
	global_position = p
	velocity = Vector3.ZERO
	_last_pos = p
