extends CharacterBody3D
## First person player: joystick walks, run button runs, dragging looks around. The player always holds a lit candle
## (modelled in Blender: wax with drips, wick, brass chamberstick) - it is the only light the player carries.

signal stepped(loudness: float)

const WALK_SPEED := 2.05
const RUN_SPEED := 3.7
const EYE_HEIGHT := 1.58

var hud
var frozen := false
var yaw := 0.0
var pitch := 0.0
var head: Node3D
var camera: Camera3D
var flashlight: SpotLight3D          # the candle's light thrown ahead (kept under this name for the level script)
var candle_light: OmniLight3D
var candle: Node3D
var _candle_base := Vector3(0.2, -0.205, -0.38)
var _t := 0.0
var blackout := false                 # jumpscare: the candle is snuffed out
var _flame_nodes: Array = []
const CANDLE_E := 1.7
const SPOT_E := 1.25
const CANDLE_GLB := "res://assets/map/candle.glb"
const FLAME_SHADER := """
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;
uniform float glow = 0.0;
float hash(float n) { return fract(sin(n) * 43758.5453); }
float noise1(float x) { float i = floor(x); float f = fract(x); return mix(hash(i), hash(i + 1.0), f * f * (3.0 - 2.0 * f)); }
void vertex() {
	// stay upright, turn to face the camera around the vertical axis
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(vec4(normalize(cross(vec3(0.0, 1.0, 0.0), INV_VIEW_MATRIX[2].xyz)), 0.0),
		vec4(0.0, 1.0, 0.0, 0.0), vec4(normalize(cross(INV_VIEW_MATRIX[0].xyz, vec3(0.0, 1.0, 0.0))), 0.0), MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}
void fragment() {
	float t = TIME;
	if (glow > 0.5) {
		float d = length(UV * 2.0 - 1.0);
		float a = pow(max(0.0, 1.0 - d), 2.4) * 0.28 * (0.88 + 0.12 * noise1(t * 9.0));
		ALBEDO = vec3(1.0, 0.55, 0.22);
		ALPHA = a;
	} else {
		float y = UV.y;                       // 0 = tip, 1 = base
		float sway = (noise1(t * 3.3) - 0.5) * 0.45 * (1.0 - y) * (1.0 - y);
		float x = (UV.x * 2.0 - 1.0) - sway;
		float w = mix(0.04, 0.6, smoothstep(0.0, 0.75, y)) * (1.0 - smoothstep(0.84, 1.0, y) * 0.85);
		w *= 0.9 + 0.1 * noise1(t * 14.0 + 3.0);
		float d = abs(x) / max(w, 0.001);
		float body = 1.0 - smoothstep(0.5, 1.0, d);
		float core = (1.0 - smoothstep(0.0, 0.6, d)) * smoothstep(0.25, 0.7, y);
		vec3 col = mix(vec3(1.0, 0.45, 0.1), vec3(1.0, 0.9, 0.62), core);
		col = mix(col, vec3(0.35, 0.45, 1.0), smoothstep(0.8, 0.95, y) * (1.0 - smoothstep(0.95, 1.0, y)) * 0.55);
		ALBEDO = col * 1.7;
		ALPHA = body * (1.0 - smoothstep(0.92, 1.0, y)) * smoothstep(0.0, 0.06, y);
	}
}
"""
var noise := 0.0                 # 0 = silent, 1 = running
var running := false
var _bob := 0.0
var _step_acc := 0.0
var _shake := 0.0
var _flicker := 0.0
var _vel_h := Vector3.ZERO

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	col.shape = cap
	col.position.y = 0.85
	add_child(col)
	head = Node3D.new()
	head.position.y = EYE_HEIGHT
	add_child(head)
	camera = Camera3D.new()
	camera.fov = 66.0
	camera.near = 0.05
	camera.far = 70.0
	camera.current = true
	head.add_child(camera)
	# warm candle light thrown ahead (soft, wide, with shadows so it never leaks through walls)
	flashlight = SpotLight3D.new()
	flashlight.light_color = Color(1.0, 0.66, 0.36)
	flashlight.light_energy = SPOT_E
	flashlight.spot_range = 12.0
	flashlight.spot_angle = 58.0
	flashlight.spot_angle_attenuation = 2.4
	flashlight.spot_attenuation = 1.1
	flashlight.shadow_enabled = true
	flashlight.shadow_bias = 0.04
	flashlight.shadow_normal_bias = 1.0
	camera.add_child(flashlight)
	_build_candle()

func _build_candle() -> void:
	candle = Node3D.new()
	candle.position = _candle_base
	candle.rotation = Vector3(0.0, deg_to_rad(-12.0), 0.0)
	camera.add_child(candle)
	var anchor_pos := Vector3(0.0024, 0.1155, 0.0)
	var model: Node3D = null
	if ResourceLoader.exists(CANDLE_GLB):
		var ps = load(CANDLE_GLB)
		if ps is PackedScene:
			model = (ps as PackedScene).instantiate()
	if model:
		candle.add_child(model)
		var a := model.find_child("flame_anchor", true, false)
		if a is Node3D:
			anchor_pos = candle.to_local((a as Node3D).global_position) if candle.is_inside_tree() else (a as Node3D).position
	else:
		model = _fallback_candle()
		candle.add_child(model)
	for n in model.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i in range(mi.mesh.get_surface_count()):
			var src := mi.mesh.surface_get_material(i)
			var nm := src.resource_name if src else ""
			mi.set_surface_override_material(i, _candle_mat(nm))
	# flame + soft glow + the light itself
	var flame := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.017, 0.04)
	flame.mesh = q
	var fm := ShaderMaterial.new()
	fm.shader = Shader.new()
	fm.shader.code = FLAME_SHADER
	flame.material_override = fm
	flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	flame.position = anchor_pos
	candle.add_child(flame)
	_flame_nodes.append(flame)
	var glow := MeshInstance3D.new()
	var gq := QuadMesh.new()
	gq.size = Vector2(0.12, 0.12)
	glow.mesh = gq
	var gm := ShaderMaterial.new()
	gm.shader = fm.shader
	gm.set_shader_parameter("glow", 1.0)
	glow.material_override = gm
	glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	glow.position = anchor_pos
	candle.add_child(glow)
	_flame_nodes.append(glow)
	candle_light = OmniLight3D.new()
	candle_light.light_color = Color(1.0, 0.6, 0.28)
	candle_light.light_energy = CANDLE_E
	candle_light.omni_range = 7.5
	candle_light.omni_attenuation = 1.15
	candle_light.position = anchor_pos + Vector3(0.0, 0.02, 0.0)
	candle.add_child(candle_light)

func _candle_mat(nm: String) -> Material:
	var m: StandardMaterial3D
	match nm:
		"candle_wax":
			m = StandardMaterial3D.new()
			m.albedo_color = Color(0.93, 0.87, 0.74)
			m.roughness = 0.42
			m.emission_enabled = true
			m.emission = Color(1.0, 0.62, 0.32)
			m.emission_energy_multiplier = 0.14
		"wick":
			m = StandardMaterial3D.new()
			m.albedo_color = Color(0.04, 0.035, 0.03)
			m.roughness = 1.0
		"wick_ember":
			m = StandardMaterial3D.new()
			m.albedo_color = Color(1.0, 0.35, 0.08)
			m.emission_enabled = true
			m.emission = Color(1.0, 0.35, 0.08)
			m.emission_energy_multiplier = 3.0
		_:
			m = (Mats.get_material("brass") as StandardMaterial3D).duplicate() as StandardMaterial3D
			m.vertex_color_use_as_albedo = false
			m.uv1_triplanar = true
			m.uv1_scale = Vector3.ONE * 18.0
	return m

func _fallback_candle() -> Node3D:
	var root := Node3D.new()
	var dish := MeshInstance3D.new()
	var dm := CylinderMesh.new()
	dm.top_radius = 0.055
	dm.bottom_radius = 0.05
	dm.height = 0.012
	dish.mesh = dm
	dish.position.y = 0.006
	dish.mesh.surface_set_material(0, null)
	root.add_child(dish)
	var wax := MeshInstance3D.new()
	var wm := CylinderMesh.new()
	wm.top_radius = 0.0166
	wm.bottom_radius = 0.0168
	wm.height = 0.08
	wax.mesh = wm
	wax.position.y = 0.052
	var mat := StandardMaterial3D.new()
	mat.resource_name = "candle_wax"
	wm.material = mat
	root.add_child(wax)
	return root

func look_delta(d: Vector2) -> void:
	if frozen:
		return
	var k := 0.085 * Settings.sensitivity
	yaw -= d.x * k
	pitch = clampf(pitch - d.y * k, -78.0, 78.0)

func face(yaw_deg: float, pitch_deg: float) -> void:
	yaw = yaw_deg
	pitch = pitch_deg

func add_shake(v: float) -> void:
	_shake = maxf(_shake, v)

func flicker_light(t: float) -> void:
	_flicker = maxf(_flicker, t)

func _physics_process(dt: float) -> void:
	rotation_degrees.y = yaw
	head.rotation_degrees.x = pitch
	var mv := Vector2.ZERO
	var want_run := false
	if hud and not frozen:
		mv = hud.move_vec
		want_run = hud.run_held
	running = want_run and mv.length() > 0.25
	var speed := RUN_SPEED if running else WALK_SPEED
	var dir := (global_transform.basis * Vector3(mv.x, 0.0, mv.y))
	dir.y = 0.0
	var target := dir * speed * minf(1.0, mv.length() * 1.15)
	_vel_h = _vel_h.lerp(target, clampf(dt * 9.0, 0.0, 1.0))
	velocity.x = _vel_h.x
	velocity.z = _vel_h.z
	velocity.y = 0.0 if is_on_floor() else velocity.y - 18.0 * dt
	move_and_slide()
	var moved := Vector2(velocity.x, velocity.z).length()
	noise = 0.0
	if moved > 0.4:
		noise = 1.0 if running else 0.4
		_bob += dt * moved * (3.6 if running else 3.2)
		_step_acc += moved * dt
		var stride := 1.2 if running else 1.55
		if _step_acc >= stride:
			_step_acc = 0.0
			Sfx.play("footstep", -6.0 if running else -10.0, randf_range(0.92, 1.08))
			stepped.emit(noise)
	var bob_amp := 0.045 if running else 0.026
	var sh := _shake * 0.025
	head.position = Vector3(sin(_bob * 0.5) * bob_amp * 0.6 + randf_range(-sh, sh), EYE_HEIGHT + absf(sin(_bob)) * bob_amp + randf_range(-sh, sh), 0.0)
	camera.rotation.z = sin(_bob * 0.5) * 0.008 * (2.0 if running else 1.0) + randf_range(-sh, sh) * 0.6
	_shake = maxf(0.0, _shake - dt * 1.5)
	# candle: flickering flame, held upright, swaying a little with each step
	_t += dt
	var fl := 0.84 + 0.08 * sin(_t * 11.0) + 0.05 * sin(_t * 23.7 + 1.3) + 0.05 * randf()
	var gust := 1.0
	if _flicker > 0.0:
		_flicker -= dt
		gust = 0.25 + 0.75 * float(randf() > 0.4)
	if blackout:
		gust = 0.0
	for f in _flame_nodes:
		(f as Node3D).visible = not blackout
	candle_light.light_energy = lerpf(candle_light.light_energy, CANDLE_E * fl * gust, clampf(dt * 18.0, 0.0, 1.0))
	flashlight.light_energy = lerpf(flashlight.light_energy, SPOT_E * (0.92 + 0.08 * fl) * gust, clampf(dt * 18.0, 0.0, 1.0))
	candle.position = _candle_base + Vector3(sin(_bob * 0.5) * 0.007, absf(sin(_bob)) * 0.009 - 0.004, 0.0)
	candle.rotation.x = -deg_to_rad(pitch) * 0.85
