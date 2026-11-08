extends Node3D
## A ritual item sitting on a pedestal: glows softly, picks itself up when the player walks close.

signal collected(item: Node3D)

var item_id := ""
var player: Node3D
var _t := randf() * 6.0
var _light: OmniLight3D
var _base_y := 0.0
var _done := false

func _ready() -> void:
	_base_y = position.y
	_light = OmniLight3D.new()
	_light.light_color = Color(1.0, 0.78, 0.4)
	_light.light_energy = 1.3
	_light.omni_range = 3.4
	_light.omni_attenuation = 1.4
	_light.position = Vector3(0, 0.35, 0)
	add_child(_light)
	var p := CPUParticles3D.new()
	p.amount = 14
	p.lifetime = 2.4
	p.preprocess = 2.0
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.18
	p.direction = Vector3.UP
	p.spread = 25.0
	p.gravity = Vector3.ZERO
	p.initial_velocity_min = 0.06
	p.initial_velocity_max = 0.16
	p.scale_amount_min = 0.5
	p.scale_amount_max = 1.0
	var qm := QuadMesh.new()
	qm.size = Vector2(0.018, 0.018)
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1.0, 0.8, 0.4)
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	qm.material = mat
	p.mesh = qm
	p.position = Vector3(0, 0.15, 0)
	add_child(p)

func _process(dt: float) -> void:
	if _done:
		return
	_t += dt
	position.y = _base_y + sin(_t * 1.7) * 0.012
	rotation.y += dt * 0.55
	_light.light_energy = 1.2 + 0.25 * sin(_t * 7.3) * sin(_t * 3.1)
	if player:
		var d := player.global_position - global_position
		d.y = 0.0
		if d.length() < 1.15:
			_done = true
			collected.emit(self)
