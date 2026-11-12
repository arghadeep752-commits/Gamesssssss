extends Node
## Simulates multitouch on the on-screen controls and measures script frame cost.

func _ready() -> void:
	await get_tree().process_frame
	SceneManager.params = {"level": 23, "from_checkpoint": false}
	var g: Game = load("res://scenes/gameplay/game.tscn").instantiate()
	get_tree().root.add_child(g)
	for i in 5: await get_tree().physics_frame
	var vp := get_viewport().get_visible_rect().size
	var p := g.player
	var x0 := p.global_position.x
	# finger 0: joystick drag to the right
	var t0 := InputEventScreenTouch.new(); t0.index = 0; t0.pressed = true; t0.position = Vector2(vp.x * 0.2, vp.y * 0.84)
	Input.parse_input_event(t0)
	Input.flush_buffered_events()
	await get_tree().physics_frame
	var d := InputEventScreenDrag.new(); d.index = 0; d.position = t0.position + Vector2(90, 0); d.relative = Vector2(90, 0)
	Input.parse_input_event(d)
	Input.flush_buffered_events()
	for i in 30: await get_tree().physics_frame
	var moved := p.global_position.x - x0
	# finger 1: jump while still holding the joystick
	var j := InputEventScreenTouch.new(); j.index = 1; j.pressed = true; j.position = Vector2(vp.x * 0.86, vp.y * 0.87)
	Input.parse_input_event(j)
	Input.flush_buffered_events()
	await get_tree().physics_frame
	await get_tree().physics_frame
	var jumped := p.velocity.y < -100 or p.machine.current_name == "jump"
	j.pressed = false
	Input.parse_input_event(j)
	Input.flush_buffered_events()
	for i in 20: await get_tree().physics_frame
	# finger 1: attack
	var a := InputEventScreenTouch.new(); a.index = 1; a.pressed = true; a.position = Vector2(vp.x * 0.65, vp.y * 0.90)
	Input.parse_input_event(a)
	Input.flush_buffered_events()
	await get_tree().physics_frame
	await get_tree().physics_frame
	var attacked := p.machine.current_name == "attack"
	a.pressed = false
	Input.parse_input_event(a)
	Input.flush_buffered_events()
	t0.pressed = false
	Input.parse_input_event(t0)
	Input.flush_buffered_events()
	print("TOUCH moved=%.0f jumped=%s attacked=%s" % [moved, jumped, attacked])
	# perf: run the level with the player moving for 600 frames
	Input.action_press("move_right")
	var total := 0
	var worst := 0
	var last := Time.get_ticks_usec()
	for i in 600:
		if i % 40 == 0: Input.action_press("jump")
		if i % 40 == 6: Input.action_release("jump")
		if i % 25 == 0: Input.action_press("attack")
		if i % 25 == 2: Input.action_release("attack")
		await get_tree().physics_frame
		var now := Time.get_ticks_usec()
		var dt := now - last
		last = now
		total += dt
		worst = max(worst, dt)
	print("PERF avg frame wall %.2f ms (includes 60fps wait), nodes=%d" % [total / 600.0 / 1000.0, get_tree().get_node_count()])
	print("PERF process %.3f ms physics %.3f ms" % [Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0])
	get_tree().quit()
