extends Node
## Time of day: the sun (and moon), the sky, sky light, fog, tone mapping and glow; the 'night' value the town's
## shaders use for lit windows and lamps.

var hour := 9.5
var hours_per_second := 1.0 / 60.0          # one game hour per real minute
var night := 0.0
var sun_up := 1.0
var sun_dir := Vector3(0.3, 0.8, -0.5)
var paused := false

var sun: DirectionalLight3D
var world_env: WorldEnvironment
var environment: Environment
var sky_mat: ShaderMaterial
var mats: Array[ShaderMaterial] = []        # materials with a 'night' uniform
var day_horizon := Color(0.72, 0.80, 0.88)
var night_horizon := Color(0.05, 0.06, 0.10)
var quality := 2


func setup(parent: Node) -> void:
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 90.0
	sun.directional_shadow_split_1 = 0.25
	sun.shadow_bias = 0.04
	sun.shadow_normal_bias = 1.2
	sun.shadow_blur = 1.0
	sun.directional_shadow_blend_splits = false
	parent.add_child(sun)

	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	if ResourceLoader.exists("res://gen/sky/day.png"):
		sky_mat.set_shader_parameter("day", load("res://gen/sky/day.png"))
	if ResourceLoader.exists("res://gen/sky/night.png"):
		sky_mat.set_shader_parameter("night_tex", load("res://gen/sky/night.png"))
	var info = G.load_json("res://gen/sky/sky.json")
	if info is Dictionary:
		if info.has("day"):
			var h: Array = info["day"]["horizon"]
			day_horizon = Color(h[0], h[1], h[2])
		if info.has("night"):
			var z: Array = info["night"]["zenith"]
			night_horizon = Color(z[0], z[1], z[2]) * 0.5
	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	sky.process_mode = Sky.PROCESS_MODE_REALTIME
	environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_sky_contribution = 0.75
	environment.ambient_light_color = Color(0.55, 0.55, 0.6)
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	environment.tonemap_exposure = 1.0
	environment.tonemap_white = 4.0
	environment.fog_enabled = true
	environment.fog_mode = Environment.FOG_MODE_DEPTH
	environment.fog_depth_begin = 180.0
	environment.fog_depth_end = 1150.0
	environment.fog_depth_curve = 1.6
	environment.fog_sky_affect = 0.0
	environment.glow_enabled = true
	environment.glow_intensity = 0.4
	environment.glow_strength = 1.0
	environment.glow_bloom = 0.04
	environment.glow_hdr_threshold = 1.0
	environment.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	environment.adjustment_enabled = true
	environment.adjustment_contrast = 1.06
	environment.adjustment_saturation = 1.12
	world_env = WorldEnvironment.new()
	world_env.environment = environment
	parent.add_child(world_env)
	tick(0.0)


func set_quality(q: int) -> void:
	quality = q
	if sun == null:
		return
	sun.shadow_enabled = q >= 1
	sun.directional_shadow_max_distance = [0.0, 60.0, 90.0][clamp(q, 0, 2)]
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL if q == 1 else DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	environment.glow_enabled = q >= 1


func register(m: ShaderMaterial) -> void:
	if m != null and not mats.has(m):
		mats.append(m)
		m.set_shader_parameter("night", night)


func clock() -> String:
	var h := int(floor(hour)) % 24
	var m := int(floor((hour - floor(hour)) * 60.0))
	return "%02d:%02d" % [h, m]


func _process(delta: float) -> void:
	if not paused:
		tick(delta)


func tick(dt: float) -> void:
	hour = fposmod(hour + dt * hours_per_second, 24.0)
	var t := (hour - 5.8) / 12.6                         # 0 at sunrise, 1 at sunset (Agartala, roughly)
	var elev := sin(clampf(t, 0.0, 1.0) * PI) * 64.0
	if t < 0.0 or t > 1.0:
		var k := (t + 0.9) if t < 0.0 else (t - 1.0)
		elev = -8.0 - 20.0 * sin(clampf(k / 0.9, 0.0, 1.0) * PI)
	var az := lerpf(100.0, 250.0, clampf(t, 0.0, 1.0))
	sun_up = clampf((elev + 2.0) / 14.0, 0.0, 1.0)
	night = 1.0 - clampf((elev + 6.0) / 12.0, 0.0, 1.0)
	var golden := clampf(1.0 - absf(elev - 6.0) / 14.0, 0.0, 1.0) * sun_up
	var e := deg_to_rad(maxf(elev, 6.0))
	var a := deg_to_rad(az)
	if night > 0.5:
		e = deg_to_rad(48.0)
		a = deg_to_rad(210.0)        # moonlight
	# azimuth from north (-Z in Godot) towards east (+X)
	sun_dir = Vector3(sin(a) * cos(e), sin(e), -cos(a) * cos(e)).normalized()
	if sun == null:
		return
	sun.look_at_from_position(Vector3.ZERO, -sun_dir, Vector3.UP if absf(sun_dir.y) < 0.99 else Vector3.FORWARD)
	var sun_c := Color(1.0, 0.96, 0.88).lerp(Color(1.1, 0.62, 0.34), golden)
	var moon := Color(0.42, 0.52, 0.78)
	sun.light_color = sun_c.lerp(moon, night)
	sun.light_energy = lerpf(lerpf(0.3, 1.05, sun_up), 0.28, night)
	sun.shadow_opacity = lerpf(0.85, 0.5, night)
	var fog := day_horizon.lerp(Color(0.92, 0.66, 0.50), golden * 0.8).lerp(night_horizon, night)
	environment.fog_light_color = fog.darkened(0.12)
	environment.fog_depth_end = lerpf(1150.0, 600.0, night)
	environment.ambient_light_energy = lerpf(0.7, 0.45, night)
	environment.tonemap_exposure = lerpf(0.92, 1.3, night)
	sky_mat.set_shader_parameter("night", clampf(night * 1.15, 0.0, 1.0))
	sky_mat.set_shader_parameter("tint", Color(1, 1, 1).lerp(Color(1.15, 0.85, 0.72), golden * 0.6))
	sky_mat.set_shader_parameter("energy", lerpf(1.05, 0.9, night))
	for m in mats:
		m.set_shader_parameter("night", night)
