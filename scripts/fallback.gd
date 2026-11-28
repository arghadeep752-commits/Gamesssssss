extends RefCounted
## Simple stand-in models made from boxes and cylinders.
## They are only used when the Sketchfab model for that object was not
## downloaded (for example when no Sketchfab token is set in GitHub).
## Every model: bottom-centre at the origin, front facing +Z.


func _mi(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	m.mesh = mesh
	m.material_override = mat
	m.position = pos
	m.rotation = rot
	parent.add_child(m)
	return m


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var b := BoxMesh.new()
	b.size = size
	return _mi(parent, b, mat, pos, rot)


func _cyl(parent: Node3D, r_top: float, r_bottom: float, h: float, pos: Vector3, mat: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var c := CylinderMesh.new()
	c.top_radius = r_top
	c.bottom_radius = r_bottom
	c.height = h
	c.radial_segments = 16
	c.rings = 1
	return _mi(parent, c, mat, pos, rot)


func _sphere(parent: Node3D, r: float, pos: Vector3, mat: Material, scl: Vector3 = Vector3.ONE) -> MeshInstance3D:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = 16
	s.rings = 8
	var m := _mi(parent, s, mat, pos)
	m.scale = scl
	return m


func _torus(parent: Node3D, inner: float, outer: float, pos: Vector3, mat: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var t := TorusMesh.new()
	t.inner_radius = inner
	t.outer_radius = outer
	t.rings = 12
	t.ring_segments = 8
	return _mi(parent, t, mat, pos, rot)


func _c(col: Color, rough: float = 0.7, metal: float = 0.0) -> StandardMaterial3D:
	return Assets.color_mat(col, rough, metal)


func make(key: String, size: Vector3) -> Node3D:
	var root := Node3D.new()
	root.name = "Stand_" + key
	var w := size.x
	var h := size.y
	var d := size.z
	var wood := Assets.get_material("wood")
	var white := _c(Color(0.93, 0.93, 0.9), 0.85)
	var ceramic := _c(Color(0.96, 0.96, 0.96), 0.12)
	var metal := _c(Color(0.72, 0.72, 0.74), 0.3, 1.0)
	var dark := _c(Color(0.08, 0.08, 0.08), 0.4)
	match key:
		"bed_single", "bed_double":
			_box(root, Vector3(w, h * 0.4, d), Vector3(0, h * 0.2, 0), wood)
			_box(root, Vector3(w * 0.96, h * 0.32, d * 0.96), Vector3(0, h * 0.56, 0), white)
			_box(root, Vector3(w * 0.98, h * 0.1, d * 0.62), Vector3(0, h * 0.74, d * 0.17), _c(Color(0.55, 0.14, 0.18), 0.9))
			_box(root, Vector3(w * 0.7, h * 0.16, d * 0.15), Vector3(0, h * 0.8, -d * 0.38), white)
			_box(root, Vector3(w, h * 1.8, 0.07), Vector3(0, h * 0.9, -d * 0.5 + 0.035), wood)
		"sofa":
			var fabric := _c(Color(0.36, 0.22, 0.17), 0.95)
			_box(root, Vector3(w, h * 0.45, d), Vector3(0, h * 0.225, 0), fabric)
			_box(root, Vector3(w, h * 0.55, d * 0.25), Vector3(0, h * 0.725, -d * 0.375), fabric)
			_box(root, Vector3(w * 0.1, h * 0.65, d), Vector3(-w * 0.45, h * 0.325, 0), fabric)
			_box(root, Vector3(w * 0.1, h * 0.65, d), Vector3(w * 0.45, h * 0.325, 0), fabric)
			_box(root, Vector3(w * 0.78, h * 0.12, d * 0.65), Vector3(0, h * 0.51, d * 0.1), _c(Color(0.45, 0.3, 0.22), 0.95))
		"tv_cabinet", "sideboard", "nightstand":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), wood)
			_box(root, Vector3(w * 0.9, h * 0.02, 0.01), Vector3(0, h * 0.55, d * 0.5 + 0.005), dark)
			_sphere(root, 0.02, Vector3(0, h * 0.75, d * 0.5 + 0.02), metal)
			_sphere(root, 0.02, Vector3(0, h * 0.3, d * 0.5 + 0.02), metal)
		"tv":
			_box(root, Vector3(w * 0.3, h * 0.08, d), Vector3(0, h * 0.04, 0), dark)
			_box(root, Vector3(w, h * 0.88, d * 0.45), Vector3(0, h * 0.54, 0), _c(Color(0.05, 0.05, 0.05), 0.35))
			_box(root, Vector3(w * 0.92, h * 0.76, 0.01), Vector3(0, h * 0.55, d * 0.23 + 0.006), _c(Color(0.01, 0.01, 0.015), 0.05))
		"coffee_table", "dining_table", "desk":
			_box(root, Vector3(w, h * 0.07, d), Vector3(0, h * 0.965, 0), wood)
			for sx in [-1.0, 1.0]:
				for sz in [-1.0, 1.0]:
					_box(root, Vector3(0.05, h * 0.93, 0.05), Vector3(sx * (w * 0.5 - 0.06), h * 0.465, sz * (d * 0.5 - 0.06)), wood)
		"chair":
			_box(root, Vector3(w, 0.05, d), Vector3(0, h * 0.5, 0), wood)
			for sx in [-1.0, 1.0]:
				for sz in [-1.0, 1.0]:
					_box(root, Vector3(0.04, h * 0.5, 0.04), Vector3(sx * (w * 0.5 - 0.03), h * 0.25, sz * (d * 0.5 - 0.03)), wood)
			_box(root, Vector3(w, h * 0.5, 0.04), Vector3(0, h * 0.75, -d * 0.5 + 0.02), wood)
		"plant":
			_cyl(root, w * 0.3, w * 0.22, h * 0.3, Vector3(0, h * 0.15, 0), _c(Color(0.6, 0.3, 0.2), 0.8))
			var leaf := _c(Color(0.18, 0.42, 0.14), 0.8)
			_sphere(root, w * 0.42, Vector3(0, h * 0.62, 0), leaf, Vector3(1, 1.3, 1))
			_sphere(root, w * 0.25, Vector3(w * 0.15, h * 0.9, 0.05), leaf)
		"kitchen_counter":
			_box(root, Vector3(w, h * 0.95, d), Vector3(0, h * 0.475, 0), _c(Color(0.85, 0.83, 0.78), 0.6))
			_box(root, Vector3(w + 0.02, h * 0.05, d + 0.02), Vector3(0, h * 0.975, 0), _c(Color(0.15, 0.15, 0.16), 0.2))
			for i in range(3):
				var x := -w * 0.5 + w * (i + 0.5) / 3.0
				_box(root, Vector3(0.02, h * 0.7, 0.01), Vector3(x + w / 6.0, h * 0.45, d * 0.5 + 0.005), dark)
				_box(root, Vector3(0.1, 0.02, 0.02), Vector3(x, h * 0.8, d * 0.5 + 0.015), metal)
		"stove":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), _c(Color(0.9, 0.9, 0.9), 0.3))
			_box(root, Vector3(w, 0.02, d), Vector3(0, h + 0.01, 0), dark)
			for bx in [-1.0, 1.0]:
				for bz in [-1.0, 1.0]:
					_cyl(root, 0.07, 0.07, 0.02, Vector3(bx * w * 0.22, h + 0.025, bz * d * 0.22), dark)
			_box(root, Vector3(w * 0.8, h * 0.45, 0.01), Vector3(0, h * 0.4, d * 0.5 + 0.005), _c(Color(0.05, 0.05, 0.05), 0.08))
		"fridge":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), _c(Color(0.92, 0.92, 0.93), 0.2))
			_box(root, Vector3(w, 0.015, 0.01), Vector3(0, h * 0.62, d * 0.5 + 0.005), dark)
			_box(root, Vector3(0.03, h * 0.25, 0.04), Vector3(w * 0.38, h * 0.8, d * 0.5 + 0.03), metal)
			_box(root, Vector3(0.03, h * 0.2, 0.04), Vector3(w * 0.38, h * 0.45, d * 0.5 + 0.03), metal)
		"bookshelf", "shelf":
			_box(root, Vector3(w, h, 0.02), Vector3(0, h * 0.5, -d * 0.5 + 0.01), wood)
			_box(root, Vector3(0.03, h, d), Vector3(-w * 0.5 + 0.015, h * 0.5, 0), wood)
			_box(root, Vector3(0.03, h, d), Vector3(w * 0.5 - 0.015, h * 0.5, 0), wood)
			var cols := [Color(0.6, 0.1, 0.1), Color(0.1, 0.3, 0.6), Color(0.15, 0.45, 0.2), Color(0.7, 0.6, 0.2), Color(0.35, 0.2, 0.4)]
			for i in range(5):
				var y := 0.03 + h * i / 4.6
				_box(root, Vector3(w, 0.03, d), Vector3(0, y, 0), wood)
				if i < 4:
					for b in range(5):
						var bh := h * 0.13 + 0.03 * float(b % 2)
						_box(root, Vector3(w * 0.12, bh, d * 0.8), Vector3(-w * 0.38 + b * w * 0.15, y + bh * 0.5 + 0.015, 0), _c(cols[(i + b) % cols.size()], 0.8))
		"toilet":
			_cyl(root, 0.15, 0.12, h * 0.5, Vector3(0, h * 0.25, d * 0.1), ceramic)
			_cyl(root, 0.2, 0.17, 0.08, Vector3(0, h * 0.54, d * 0.12), ceramic)
			_box(root, Vector3(w, h * 0.42, d * 0.25), Vector3(0, h * 0.75, -d * 0.37), ceramic)
		"sink":
			_cyl(root, 0.08, 0.1, h * 0.8, Vector3(0, h * 0.4, -d * 0.1), ceramic)
			_box(root, Vector3(w, h * 0.18, d), Vector3(0, h * 0.9, 0), ceramic)
			_cyl(root, 0.015, 0.015, 0.15, Vector3(0, h + 0.075, -d * 0.35), metal)
		"washing_machine":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), _c(Color(0.95, 0.95, 0.95), 0.25))
			_cyl(root, w * 0.3, w * 0.3, 0.03, Vector3(0, h * 0.45, d * 0.5 + 0.01), _c(Color(0.2, 0.25, 0.3), 0.05), Vector3(PI * 0.5, 0, 0))
			_box(root, Vector3(w, h * 0.15, 0.01), Vector3(0, h * 0.9, d * 0.5 + 0.005), _c(Color(0.7, 0.7, 0.72), 0.4))
		"cardboard_box":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), _c(Color(0.66, 0.49, 0.3), 0.9))
			_box(root, Vector3(w * 0.15, 0.005, d + 0.004), Vector3(0, h + 0.002, 0), _c(Color(0.8, 0.7, 0.5), 0.5))
		"wardrobe":
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), wood)
			_box(root, Vector3(0.01, h * 0.95, 0.01), Vector3(0, h * 0.5, d * 0.5 + 0.005), dark)
			_box(root, Vector3(0.02, 0.2, 0.03), Vector3(-0.06, h * 0.5, d * 0.5 + 0.02), metal)
			_box(root, Vector3(0.02, 0.2, 0.03), Vector3(0.06, h * 0.5, d * 0.5 + 0.02), metal)
		"dressing_table":
			_box(root, Vector3(w, h * 0.5, d), Vector3(0, h * 0.25, 0), wood)
			_box(root, Vector3(w * 0.75, h * 0.48, 0.04), Vector3(0, h * 0.75, -d * 0.5 + 0.04), wood)
			_box(root, Vector3(w * 0.65, h * 0.4, 0.01), Vector3(0, h * 0.75, -d * 0.5 + 0.065), _c(Color(0.9, 0.92, 0.95), 0.02, 1.0))
		"safe":
			var steel := _c(Color(0.18, 0.2, 0.22), 0.35, 0.8)
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), steel)
			_box(root, Vector3(w * 0.8, h * 0.8, 0.03), Vector3(0, h * 0.5, d * 0.5 + 0.015), _c(Color(0.25, 0.27, 0.3), 0.3, 0.8))
			_cyl(root, 0.06, 0.06, 0.03, Vector3(-w * 0.12, h * 0.55, d * 0.5 + 0.045), metal, Vector3(PI * 0.5, 0, 0))
			_box(root, Vector3(0.03, 0.14, 0.04), Vector3(w * 0.25, h * 0.5, d * 0.5 + 0.05), metal)
		"school_bag":
			var red := _c(Color(0.75, 0.1, 0.08), 0.8)
			_box(root, Vector3(w, h, d), Vector3(0, h * 0.5, 0), red)
			_box(root, Vector3(w * 0.75, h * 0.4, 0.05), Vector3(0, h * 0.3, d * 0.5 + 0.02), _c(Color(0.6, 0.08, 0.06), 0.8))
		"key_old", "key_gold":
			var km := _c(Color(1.0, 0.78, 0.25), 0.2, 1.0) if key == "key_gold" else _c(Color(0.75, 0.75, 0.78), 0.25, 1.0)
			var l := maxf(w, d)
			_torus(root, l * 0.1, l * 0.18, Vector3(-l * 0.33, 0.006, 0), km)
			_box(root, Vector3(l * 0.62, 0.01, l * 0.07), Vector3(l * 0.12, 0.006, 0), km)
			_box(root, Vector3(l * 0.07, 0.01, l * 0.14), Vector3(l * 0.32, 0.006, l * 0.08), km)
			_box(root, Vector3(l * 0.06, 0.01, l * 0.1), Vector3(l * 0.2, 0.006, l * 0.06), km)
		"hammer":
			var l := maxf(w, d)
			_box(root, Vector3(l * 0.85, 0.03, 0.035), Vector3(-l * 0.07, 0.018, 0), wood)
			_box(root, Vector3(0.045, 0.04, l * 0.38), Vector3(l * 0.4, 0.022, 0), metal)
		"bolt_cutter":
			var l := maxf(w, d)
			var red := _c(Color(0.8, 0.08, 0.06), 0.45)
			_box(root, Vector3(l * 0.6, 0.025, 0.03), Vector3(-l * 0.18, 0.016, 0.035), red, Vector3(0, 0.08, 0))
			_box(root, Vector3(l * 0.6, 0.025, 0.03), Vector3(-l * 0.18, 0.016, -0.035), red, Vector3(0, -0.08, 0))
			_box(root, Vector3(l * 0.3, 0.035, 0.05), Vector3(l * 0.3, 0.02, 0), metal)
		"padlock":
			var brass := _c(Color(0.85, 0.65, 0.25), 0.3, 1.0)
			var l := maxf(w, maxf(h, d))
			_box(root, Vector3(l * 0.55, l * 0.45, l * 0.22), Vector3(0, l * 0.225, 0), brass)
			_torus(root, l * 0.14, l * 0.2, Vector3(0, l * 0.5, 0), metal, Vector3(PI * 0.5, 0, 0))
		"chain":
			var l := maxf(w, d)
			var n := 12
			for i in range(n):
				var x := -l * 0.5 + l * (i + 0.5) / n
				var rot := Vector3(PI * 0.5, 0, 0) if i % 2 == 1 else Vector3.ZERO
				_torus(root, l * 0.022, l * 0.04, Vector3(x, l * 0.04, 0), metal, rot)
		"planks":
			var l := maxf(w, d)
			_box(root, Vector3(l, 0.17, 0.035), Vector3(0, 0.085, 0), wood)
			for nx in [-0.42, 0.42]:
				_cyl(root, 0.012, 0.012, 0.01, Vector3(nx * l, 0.085, 0.02), metal, Vector3(PI * 0.5, 0, 0))
		_:
			_box(root, size, Vector3(0, h * 0.5, 0), wood)
	return root


## The stand-in Scary Aunty: saree, blouse, hair bun and a rolling pin.
## Arms are on pivots named "ArmL" / "ArmR" so the AI can swing them.
func make_aunty() -> Node3D:
	var root := Node3D.new()
	root.name = "AuntyStandIn"
	var skin := _c(Color(0.62, 0.42, 0.3), 0.6)
	var saree := _c(Color(0.55, 0.05, 0.1), 0.75)
	var border := _c(Color(0.85, 0.65, 0.15), 0.4, 0.6)
	var blouse := _c(Color(0.12, 0.25, 0.15), 0.7)
	var hair := _c(Color(0.04, 0.03, 0.03), 0.5)
	# Saree skirt (feet hidden) + golden border
	_cyl(root, 0.2, 0.3, 0.95, Vector3(0, 0.475, 0), saree)
	_cyl(root, 0.305, 0.305, 0.06, Vector3(0, 0.05, 0), border)
	# Body
	_cyl(root, 0.17, 0.2, 0.5, Vector3(0, 1.2, 0), blouse)
	_box(root, Vector3(0.12, 0.62, 0.05), Vector3(0.05, 1.18, -0.2), saree, Vector3(0, 0, 0.45))
	# Neck + head
	_cyl(root, 0.05, 0.06, 0.1, Vector3(0, 1.49, 0), skin)
	_sphere(root, 0.12, Vector3(0, 1.62, 0), skin, Vector3(1, 1.1, 1))
	_sphere(root, 0.125, Vector3(0, 1.67, 0.02), hair, Vector3(1.02, 0.8, 1.05))
	_sphere(root, 0.075, Vector3(0, 1.66, 0.15), hair)
	# Angry eyes + red bindi (she looks towards -Z)
	var eye := _c(Color(1, 0.95, 0.9), 0.3)
	var pupil := _c(Color(0.5, 0.0, 0.0), 0.2)
	for ex in [-0.045, 0.045]:
		_sphere(root, 0.022, Vector3(ex, 1.64, -0.105), eye)
		_sphere(root, 0.011, Vector3(ex, 1.64, -0.125), pupil)
		_box(root, Vector3(0.05, 0.008, 0.01), Vector3(ex, 1.675, -0.115), hair, Vector3(0, 0, 0.35 if ex < 0.0 else -0.35))
	_sphere(root, 0.009, Vector3(0, 1.69, -0.118), _c(Color(0.85, 0.0, 0.0), 0.3))
	# Arms on shoulder pivots
	for side in [-1.0, 1.0]:
		var pivot := Node3D.new()
		pivot.name = "ArmL" if side < 0.0 else "ArmR"
		pivot.position = Vector3(side * 0.23, 1.4, 0)
		root.add_child(pivot)
		var arm := CapsuleMesh.new()
		arm.radius = 0.05
		arm.height = 0.62
		_mi(pivot, arm, skin, Vector3(0, -0.3, 0))
		_sphere(pivot, 0.055, Vector3(0, -0.62, 0), skin)
		if side > 0.0:
			# Rolling pin (belan) in her right hand
			_cyl(pivot, 0.025, 0.025, 0.42, Vector3(0, -0.64, -0.05), Assets.get_material("wood"), Vector3(PI * 0.5, 0, 0))
	return root
