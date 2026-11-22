class_name Fx
extends Node3D
## Short-lived camera-facing glows: muzzle flashes, sparks, explosions, fires.

static var inst: Fx
var mat: ShaderMaterial
var pool: Array = []         # [MeshInstance3D, until, life, size, color]


static func init_fx(parent: Node) -> void:
	inst = Fx.new()
	inst.name = "fx"
	parent.add_child(inst)
	inst.mat = ShaderMaterial.new()
	inst.mat.shader = load("res://shaders/glow.gdshader")
	inst.mat.set_shader_parameter("tex", Ui.tex("glow"))
	inst.mat.set_shader_parameter("night", 1.0)
	inst.mat.set_shader_parameter("boost", 2.5)


static func flash(p: Vector3, size: float, c: Color, time: float) -> void:
	if inst:
		inst._add(p, size, c, time)


func _quad(size: float, c: Color) -> ArrayMesh:
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3.ZERO, Vector3.ZERO, Vector3.ZERO, Vector3.ZERO])
	arr[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arr[Mesh.ARRAY_TEX_UV2] = PackedVector2Array([Vector2(size, 0), Vector2(size, 0), Vector2(size, 0), Vector2(size, 0)])
	arr[Mesh.ARRAY_COLOR] = PackedColorArray([c, c, c, c])
	arr[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


func _add(p: Vector3, size: float, c: Color, time: float) -> void:
	var slot: Array = []
	for e in pool:
		if not e[0].visible:
			slot = e
			break
	if slot.is_empty():
		if pool.size() >= 40:
			return
		var mi := MeshInstance3D.new()
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.custom_aabb = AABB(Vector3(-10, -10, -10), Vector3(20, 20, 20))
		add_child(mi)
		slot = [mi, 0.0, 0.0, 0.0, Color.WHITE]
		pool.append(slot)
	var m: MeshInstance3D = slot[0]
	m.mesh = _quad(size, c)
	m.global_position = p
	m.visible = true
	slot[1] = G.now + time
	slot[2] = time
	slot[3] = size
	slot[4] = c


func _process(_d: float) -> void:
	for e in pool:
		var m: MeshInstance3D = e[0]
		if not m.visible:
			continue
		var left: float = e[1] - G.now
		if left <= 0.0:
			m.visible = false
			continue
		var s: float = e[3] * (0.6 + 0.4 * left / maxf(0.001, e[2]))
		m.scale = Vector3.ONE * (s / maxf(0.001, e[3]))
