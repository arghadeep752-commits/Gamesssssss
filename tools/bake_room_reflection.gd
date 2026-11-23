extends Node
## Bakes assets/textures/room_reflection.png: a 360 degree picture of the room taken from its centre.
## It is used as the WorldEnvironment's sky, so the floor, the door and the brass knob reflect the
## room (the mobile-friendly Compatibility renderer has no working reflection probes).
##
## Needs a computer with a screen (or Xvfb):
##   godot --rendering-driver opengl3 --path . --script tools/bake_runner.gd

const FACE_SIZE := 512
const CAPTURE_POS := Vector3(0, 1.45, 0)
const OUT := "res://assets/textures/room_reflection.png"

var _viewport: SubViewport
var _camera: Camera3D


func _ready() -> void:
	var main: Node3D = load("res://main.tscn").instantiate()
	add_child(main)
	main.get_node("HUD").queue_free()
	main.get_node("Lamp/Bulb").visible = false   # the lamp's own highlight comes from the light itself

	_viewport = SubViewport.new()
	_viewport.size = Vector2i(FACE_SIZE, FACE_SIZE)
	_viewport.msaa_3d = Viewport.MSAA_4X
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_viewport)
	_camera = Camera3D.new()
	_camera.fov = 90.0
	_camera.near = 0.02
	_viewport.add_child(_camera)
	_camera.current = true
	await get_tree().create_timer(0.5).timeout

	var tmp := ProjectSettings.globalize_path("res://tools/.bake")
	DirAccess.make_dir_recursive_absolute(tmp)

	# the room lit exactly like in the game (lamp + the WorldEnvironment's ambient colour),
	# without tone mapping or glow so the picture keeps the real brightness
	var game_env: Environment = main.get_node("WorldEnvironment").environment
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = game_env.ambient_light_color
	env.ambient_light_energy = game_env.ambient_light_energy
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	_camera.environment = env
	await get_tree().create_timer(0.3).timeout
	await _capture(tmp, ProjectSettings.globalize_path(OUT))
	print("BAKED ", OUT)
	get_tree().quit()


func _capture(tmp: String, panorama_path: String) -> void:
	# six 90 degree views: +X, -X, +Y, -Y, +Z, -Z
	var dirs := [Vector3.RIGHT, Vector3.LEFT, Vector3.UP, Vector3.DOWN, Vector3.BACK, Vector3.FORWARD]
	var ups := [Vector3.UP, Vector3.UP, Vector3.BACK, Vector3.FORWARD, Vector3.UP, Vector3.UP]
	var faces := []
	for i in 6:
		_camera.global_transform = Transform3D(Basis.looking_at(dirs[i], ups[i]), CAPTURE_POS)
		for f in 3:
			await RenderingServer.frame_post_draw
		var path := "%s/face_%d.png" % [tmp, i]
		_viewport.get_texture().get_image().save_png(path)
		var b := _camera.global_transform.basis
		faces.append({"path": path, "right": [b.x.x, b.x.y, b.x.z], "up": [b.y.x, b.y.y, b.y.z], "forward": [-b.z.x, -b.z.y, -b.z.z]})
	var json := tmp + "/faces.json"
	var f := FileAccess.open(json, FileAccess.WRITE)
	f.store_string(JSON.stringify({"faces": faces, "fov": 90.0}))
	f.close()
	var output := []
	var code := OS.execute("python3", [ProjectSettings.globalize_path("res://tools/cube_to_panorama.py"), json, panorama_path], output, true)
	print("".join(output))
	assert(code == 0, "panorama conversion failed")
