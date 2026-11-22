extends Node
## Global state and helpers (autoload "G"): physics layers, colours, links to the game's main parts, JSON loading.

const L_WORLD := 1
const L_VEHICLE := 2
const L_PED := 4
const L_PLAYER := 8

const SAFFRON := Color(1.0, 0.6, 0.1)
const GREEN := Color(0.25, 0.8, 0.3)
const RED := Color(0.92, 0.22, 0.18)
const BLUE := Color(0.2, 0.5, 0.95)
const DARK := Color(0.08, 0.08, 0.1, 0.88)
const YELLOW := Color(1.0, 0.85, 0.15)
const MONEY := Color(0.45, 0.78, 0.38)

var game: Node = null
var city: Node3D = null
var env: Node = null
var player: Node3D = null
var cam: Node = null
var hud: Node = null
var traffic: Node = null
var audio: Node = null
var menus: Node = null
var test_mode := false
var now := 0.0                    # game time (stops while paused)
var dt := 0.0
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	rng.randomize()
	test_mode = "--dg-test" in OS.get_cmdline_user_args() or OS.has_feature("dgtest")


func note(msg: String) -> void:
	print("[DG] " + msg)


func load_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		push_warning("missing " + path)
		return null
	return JSON.parse_string(FileAccess.get_file_as_string(path))


func v3(a) -> Vector3:
	if a == null or a.size() < 3:
		return Vector3.ZERO
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


func flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)


## Yaw (degrees, Godot: rotation about +Y) that makes -Z look along 'dir'.
func yaw_of(dir: Vector3) -> float:
	return rad_to_deg(atan2(-dir.x, -dir.z))


func fwd(yaw_deg: float) -> Vector3:
	var a := deg_to_rad(yaw_deg)
	return Vector3(-sin(a), 0.0, -cos(a))


func rupees(v: int) -> String:
	# Indian grouping: 1,25,000
	var s := str(abs(v))
	if s.length() > 3:
		var head := s.substr(0, s.length() - 3)
		var tail := s.substr(s.length() - 3)
		var parts: Array[String] = []
		while head.length() > 2:
			parts.push_front(head.substr(head.length() - 2))
			head = head.substr(0, head.length() - 2)
		if head.length() > 0:
			parts.push_front(head)
		s = ",".join(parts) + "," + tail
	return ("-" if v < 0 else "") + s
