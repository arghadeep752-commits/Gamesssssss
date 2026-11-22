class_name Hud
extends Control
## The playing screen in the style of the GTA V fan-made mobile games: see-through round buttons with white icons,
## the minimap in the bottom-left corner with health and armour under it, money, stars and the weapon top-right.

static var I: Hud
static var scripted := false
static var s_fire := false
static var s_gas := false
static var s_brake := false
static var s_up := false
static var s_move := Vector2.ZERO

const GLASS := Color(1, 1, 1, 0.62)
const MAP_W := 340.0
const MAP_H := 210.0

var stick: Stick
var fire: HoldBtn
var jump_b: HoldBtn
var sprint_b: HoldBtn
var enter_b: HoldBtn
var gas: HoldBtn
var brake_b: HoldBtn
var horn_b: HoldBtn
var exit_b: HoldBtn
var up_b: HoldBtn
var down_b: HoldBtn
var weapon_b: HoldBtn
var context: HoldBtn
var foot: Control
var drive: Control
var heli: Control
var toast_box: Control
var money_t: Label
var speed_t: Label
var ammo_t: Label
var toast_t: Label
var zone_t: Label
var big_t: Label
var clock_t: Label
var fps_t: Label
var radio_t: Label
var health_bar: Control
var armor_bar: Control
var flash_r: ColorRect
var wpn_icon: Control
var rupee: Control
var map_rect: TextureRect
var map_clip: Control
var arrow: Control
var blip_root: Control
var star_imgs: Array = []
var blips: Array = []          # [Control, Vector3]
var cop_blips: Array = []
var toast_until := 0.0
var zone_until := 0.0
var big_until := 0.0
var flash_a := 0.0
var radio_until := 0.0
var last_zone := ""
var ctx_action := Callable()
var fps_acc := 0.0
var fps_n := 0
var show_fps := false
var map_tex: Texture2D


static func create(parent: Control) -> Hud:
	var h := Hud.new()
	h.name = "HUD"
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.process_mode = Node.PROCESS_MODE_ALWAYS
	parent.add_child(h)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	I = h
	G.hud = h
	h.build()
	return h


static func real() -> float:
	return Time.get_ticks_msec() / 1000.0


func btn(parent: Node, icon: String, anchor: Vector2, pos: Vector2, size: float, click := Callable()) -> HoldBtn:
	var b := Ui.round_btn(parent, icon, "", GLASS, anchor, pos, size, click)
	if b.icon:
		Ui.place(b.icon, Ui.C, Vector2.ZERO, Vector2(size * 0.5, size * 0.5))
	return b


func build() -> void:
	var lp := LookPad.new()
	lp.name = "look"
	add_child(lp)
	lp.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	# joystick: anywhere on the left, above the minimap
	var sz := Stick.new()
	sz.name = "stickzone"
	add_child(sz)
	Ui.place(sz, Ui.BL, Vector2(0, 250), Vector2(760, 620))
	var base := Ui.img(sz, "ring", Color(1, 1, 1, 0.9), Ui.BL, Vector2(250 - 115, 190 - 115), Vector2(230, 230))
	var knob := Ui.img(base, "circle", Color(1, 1, 1, 0.9), Ui.C, Vector2.ZERO, Vector2(100, 100))
	# Stick works in plain positions (top-left anchors)
	for c in [base, knob]:
		var r := Rect2(c.position, c.size)
		c.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
		c.position = r.position
		c.size = r.size
	base.position = Vector2(250 - 115, 620 - 190 - 115)
	knob.position = (base.size - knob.size) * 0.5
	sz.setup(base, knob)
	stick = sz

	# minimap: bottom-left rectangle, like GTA V
	var frame := Ui.img(self, "", Color(0, 0, 0, 0.75), Ui.BL, Vector2(22, 34), Vector2(MAP_W + 8, MAP_H + 8))
	map_clip = Ui.box(frame, "minimap", Ui.C, Vector2.ZERO, Vector2(MAP_W, MAP_H))
	map_clip.clip_contents = true
	var big2 := sqrt(MAP_W * MAP_W + MAP_H * MAP_H) + 4.0
	map_rect = TextureRect.new()
	map_rect.name = "map"
	map_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	map_tex = load("res://gen/city/map.png") if ResourceLoader.exists("res://gen/city/map.png") else null
	var at := AtlasTexture.new()
	at.atlas = map_tex
	at.filter_clip = true
	map_rect.texture = at
	map_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	map_rect.stretch_mode = TextureRect.STRETCH_SCALE
	map_clip.add_child(map_rect)
	Ui.place(map_rect, Ui.C, Vector2.ZERO, Vector2(big2, big2))
	blip_root = Ui.box(map_clip, "blips", Ui.C, Vector2.ZERO, Vector2(MAP_W, MAP_H))
	arrow = Ui.img(map_clip, "arrow", Color.WHITE, Ui.C, Vector2(0, -20), Vector2(26, 26))
	# health (green) and armour (blue) under the map
	Ui.img(self, "", Color(0, 0, 0, 0.75), Ui.BL, Vector2(22, 16), Vector2(MAP_W + 8, 16))
	health_bar = Ui.img(self, "", Color(0.34, 0.69, 0.31), Ui.BL, Vector2(26, 20), Vector2(MAP_W * 0.6 - 4, 8))
	armor_bar = Ui.img(self, "", Color(0.24, 0.55, 0.85), Ui.BL, Vector2(26 + MAP_W * 0.6, 20), Vector2(MAP_W * 0.4 - 4, 8))

	# top-right: weapon, money, stars (GTA layout)
	weapon_b = Ui.round_btn(self, "", "", Color(0, 0, 0, 0.01), Ui.TR, Vector2(-24, -14), 120, func():
		if Player.I:
			Player.I.next_weapon(1))
	wpn_icon = Ui.img(weapon_b, "i_fist", Color.WHITE, Ui.C, Vector2(0, 6), Vector2(92, 92))
	ammo_t = Ui.txt(self, "", 34, Color.WHITE, "right", Ui.TR, Vector2(-150, -50), Vector2(240, 40))
	money_t = Ui.txt(self, "0", 64, G.MONEY, "right", Ui.TR, Vector2(-26, -132), Vector2(560, 74), Ui.title)
	rupee = Ui.img(self, "i_rupee", G.MONEY, Ui.TR, Vector2(-300, -140), Vector2(46, 46))
	for i in 5:
		star_imgs.append(Ui.img(self, "i_star", Color(1, 1, 1, 0.22), Ui.TR, Vector2(-28 - (4 - i) * 50, -206), Vector2(44, 44)))
	clock_t = Ui.txt(self, "", 28, Color(1, 1, 1, 0.85), "right", Ui.TR, Vector2(-28, -252), Vector2(200, 34))
	btn(self, "pause", Ui.TL, Vector2(22, -22), 78, func(): G.menus.pause())
	btn(self, "camera", Ui.TL, Vector2(110, -22), 78, func():
		if G.cam:
			G.cam.dist = 3.4 if G.cam.dist > 5.0 else (6.5 if G.cam.dist > 4.0 else 4.4))
	btn(self, "phone", Ui.BL, Vector2(MAP_W + 44, 40), 86, func(): G.menus.phone())
	fps_t = Ui.txt(self, "", 24, Color.YELLOW, "left", Ui.TL, Vector2(200, -34), Vector2(300, 30))

	# on foot
	foot = Ui.box(self, "foot", Ui.BR, Vector2.ZERO, Vector2(600, 560))
	fire = btn(foot, "fist", Ui.BR, Vector2(-46, 64), 170)
	jump_b = btn(foot, "jump", Ui.BR, Vector2(-246, 46), 116, func():
		if Player.I:
			Player.I.jump = true)
	sprint_b = btn(foot, "sprint", Ui.BR, Vector2(-56, 262), 116)
	enter_b = btn(foot, "car", Ui.BR, Vector2(-236, 216), 116, func():
		if Player.I and Player.I.near_vehicle:
			Player.I.enter_vehicle(Player.I.near_vehicle))
	# driving
	drive = Ui.box(self, "drive", Ui.BR, Vector2.ZERO, Vector2(600, 560))
	gas = btn(drive, "gas", Ui.BR, Vector2(-46, 64), 170)
	brake_b = btn(drive, "brake", Ui.BR, Vector2(-246, 46), 130)
	horn_b = btn(drive, "horn", Ui.BR, Vector2(-56, 262), 106, func():
		if Player.I and Player.I.vehicle:
			Player.I.vehicle.horn())
	exit_b = btn(self, "exit", Ui.BR, Vector2(-236, 236), 106, func():
		if Player.I:
			Player.I.exit_vehicle())
	# helicopter
	heli = Ui.box(self, "heli", Ui.BR, Vector2.ZERO, Vector2(600, 560))
	up_b = btn(heli, "up", Ui.BR, Vector2(-56, 262), 150)
	down_b = btn(heli, "down", Ui.BR, Vector2(-56, 64), 150)
	speed_t = Ui.txt(self, "", 46, Color.WHITE, "lower_right", Ui.BR, Vector2(-330, 30), Vector2(300, 60), Ui.title)
	radio_t = Ui.txt(self, "", 34, Color.WHITE, "center", Ui.T, Vector2(0, -30), Vector2(900, 50))
	# context action (shops, house, hospital)
	context = Ui.wide(self, "SHOP", Color(0, 0, 0, 0.7), Ui.B, Vector2(0, 150), Vector2(360, 86), func():
		if ctx_action.is_valid():
			ctx_action.call(), 40)
	context.visible = false
	# GTA-style help box (top-left) for messages
	toast_box = Ui.img(self, "", Color(0, 0, 0, 0.78), Ui.TL, Vector2(22, -112), Vector2(600, 84))
	toast_t = Ui.txt(toast_box, "", 34, Color.WHITE, "left", Ui.C, Vector2.ZERO, Vector2(570, 80), Ui.font, false)
	toast_box.visible = false
	zone_t = Ui.txt(self, "", 52, Color.WHITE, "center", Ui.B, Vector2(0, 40), Vector2(1000, 70), Ui.title)
	big_t = Ui.txt(self, "", 200, G.RED, "center", Ui.C, Vector2(0, 40), Vector2(1600, 260), Ui.title)
	flash_r = Ui.img(self, "", Color(0.8, 0, 0, 0), Ui.C, Vector2.ZERO, Vector2(4000, 3000)) as ColorRect
	build_blips()


func build_blips() -> void:
	if G.city == null:
		return
	for p in G.city.points:
		var icon := ""
		var c := Color.WHITE
		match p["kind"]:
			"house":
				icon = "house"
				c = Color(0.4, 0.9, 0.4)
			"gunshop":
				icon = "pistol"
				c = Color(1.0, 0.4, 0.35)
			"clothes":
				icon = "shirt"
				c = Color(0.85, 0.55, 1.0)
			"hospital":
				icon = "cross"
				c = Color(1.0, 0.35, 0.35)
			"police":
				icon = "badge"
				c = Color(0.45, 0.65, 1.0)
			"boat":
				icon = "boat"
				c = Color(0.45, 0.85, 1.0)
			"vehicle":
				if p["model"] == "helicopter":
					icon = "heli"
					c = Color(1.0, 0.85, 0.3)
		if icon == "":
			continue
		var bg := Ui.img(blip_root, "mask_circle", Color(0, 0, 0, 0.8), Ui.C, Vector2.ZERO, Vector2(30, 30))
		Ui.img(bg, "i_" + icon, c, Ui.C, Vector2.ZERO, Vector2(21, 21))
		blips.append([bg, p["p"]])
	for i in 14:
		var b := Ui.img(blip_root, "mask_circle", Color(0.3, 0.5, 1.0), Ui.C, Vector2.ZERO, Vector2(12, 12))
		b.visible = false
		cop_blips.append(b)


static func toast(s: String, c := Color.WHITE, time := 2.8) -> void:
	if I == null:
		return
	I.toast_t.text = s
	Ui.txt_color(I.toast_t, Color.WHITE if c == Color.WHITE else c.lerp(Color.WHITE, 0.25))
	I.toast_until = real() + time
	I.toast_box.visible = true


static func big(s: String, c: Color, time: float) -> void:
	if I == null:
		return
	I.big_t.text = s
	Ui.txt_color(I.big_t, c)
	I.big_until = real() + time


static func hurt_flash() -> void:
	if I:
		I.flash_a = 0.4


static func stars_changed() -> void:
	if I == null:
		return
	for i in I.star_imgs.size():
		I.star_imgs[i].scale = Vector2.ONE * (1.3 if i < Wanted.stars else 1.0)


static func radio(s: String) -> void:
	if I:
		I.radio_t.text = s
		I.radio_until = real() + 3.0


func set_context(label: String, a: Callable) -> void:
	ctx_action = a
	var on := label != ""
	if context.visible != on:
		context.visible = on
	if on and context.label.text != label:
		context.label.text = label


func _process(delta: float) -> void:
	var p := Player.I
	if p == null or not visible:
		return
	var dt := delta
	var v := p.vehicle
	var in_v := v != null
	var is_heli := in_v and v.is_heli()
	foot.visible = not in_v
	drive.visible = in_v and not is_heli
	heli.visible = is_heli
	exit_b.visible = in_v
	enter_b.visible = not in_v and p.near_vehicle != null
	if enter_b.visible:
		var ic := "i_heli" if p.near_vehicle.is_heli() else ("i_boat" if p.near_vehicle.is_boat() else "i_car")
		Ui.set_sprite(enter_b.icon, ic)
	# inputs (the play test drives the same inputs through 'scripted')
	var mv := stick.value
	var kb := Vector2(Input.get_axis("ui_left", "ui_right"), Input.get_axis("ui_down", "ui_up"))
	mv = (mv + kb).limit_length(1.0)
	var fire_h := fire.held
	var sprint_h := sprint_b.held
	var gas_h := gas.held
	var brake_h := brake_b.held
	var up_h := up_b.held
	var down_h := down_b.held
	if scripted:
		mv = s_move
		fire_h = s_fire
		sprint_h = false
		gas_h = s_gas
		brake_h = s_brake
		up_h = s_up
		down_h = false
	p.move = mv
	p.fire = fire_h
	p.sprint = sprint_h
	if in_v:
		v.steer = move_toward(v.steer, mv.x, dt * (3.5 if v.is_bike() else 4.5))
		if is_heli:
			v.throttle = mv.y
			v.lift = (1.0 if up_h else 0.0) - (1.0 if down_h else 0.0)
		else:
			var thr := 1.0 if gas_h else 0.0
			if brake_h:
				thr = 0.0 if v.forward_speed() > 1.5 else -1.0
			if absf(mv.y) > 0.5 and not gas_h and not brake_h:
				thr = mv.y if mv.y > 0.0 else (0.0 if v.forward_speed() > 1.5 else mv.y)
			v.throttle = thr
			v.brake = 1.0 if (brake_h and v.forward_speed() > 1.5) or (mv.y < -0.5 and v.forward_speed() > 1.5) else 0.0
			v.handbrake = brake_h and gas_h
		var kmh := int(round(v.speed() * 3.6))
		speed_t.text = ("%d KM/H  %d M" % [kmh, int(v.global_position.y)]) if is_heli else ("%d KM/H" % kmh)
	else:
		speed_t.text = ""
	if real() > radio_until:
		radio_t.text = ""
	# weapon, money, health
	var d := p.def()
	Ui.set_sprite(wpn_icon, "i_" + d["icon"])
	ammo_t.text = "" if d["melee"] else "%d  %d" % [p.clip[d["id"]], p.ammo[d["id"]]]
	Ui.set_sprite(fire.icon, ("i_" + d["icon"]) if d["melee"] else "i_target")
	money_t.text = G.rupees(p.money)
	Ui.set_pos(rupee, Ui.TR, Vector2(-26.0 - Ui.text_width(money_t) - 52.0, -146.0))
	health_bar.size.x = (MAP_W * 0.6 - 4.0) * clampf(p.health / p.max_health, 0.0, 1.0)
	Ui.set_color(health_bar, Color(0.8, 0.2, 0.15) if p.health < 30.0 else Color(0.34, 0.69, 0.31))
	armor_bar.size.x = (MAP_W * 0.4 - 4.0) * clampf(p.armor / 100.0, 0.0, 1.0)
	clock_t.text = G.env.clock()
	for i in star_imgs.size():
		var on := i < Wanted.stars
		var blink := (1.0 if sin(real() * 10.0) > 0.0 else 0.35) if Wanted.escape() > 0.5 and on else 1.0
		Ui.set_color(star_imgs[i], Color(1, 1, 1, blink) if on else Color(1, 1, 1, 0.2))
		star_imgs[i].scale = star_imgs[i].scale.lerp(Vector2.ONE, minf(1.0, dt * 4.0))
	minimap(p)
	# messages
	if real() > toast_until and toast_box.visible:
		toast_box.visible = false
	if real() > big_until:
		big_t.text = ""
	var zone: String = G.city.zone_at(p.global_position) if G.city else ""
	if zone != last_zone:
		last_zone = zone
		zone_t.text = zone
		zone_until = real() + 4.0
	zone_t.modulate.a = clampf(zone_until - real(), 0.0, 1.0)
	flash_a = move_toward(flash_a, (0.12 + 0.08 * sin(real() * 6.0)) if p.health < 25.0 and not p.dead else 0.0, dt * 0.8)
	flash_r.color = Color(0.7, 0, 0, flash_a)
	fps_acc += dt
	fps_n += 1
	if fps_acc > 0.5:
		fps_t.text = ("%d FPS" % int(round(fps_n / fps_acc))) if show_fps else ""
		fps_acc = 0.0
		fps_n = 0


func minimap(p: Player) -> void:
	if map_tex == null:
		return
	var H: float = G.city.half
	var pos: Vector3 = p.vehicle.global_position if p.vehicle else p.global_position
	var rng := 260.0 if p.vehicle else 170.0          # metres across the width of the minimap
	var k := MAP_W / rng                              # pixels per metre
	var side := map_rect.size.x
	var w := side / k                                  # metres shown across the (square) map picture
	var tw := float(map_tex.get_width())
	var px := w / (2.0 * H) * tw
	var at: AtlasTexture = map_rect.texture
	at.region = Rect2((pos.x + H) / (2.0 * H) * tw - px * 0.5, (pos.z + H) / (2.0 * H) * tw - px * 0.5, px, px)
	# the map turns with the camera so up is where the camera looks; the player sits a little below the centre
	var off := Vector2(0.0, 20.0)
	var cam_yaw: float = G.cam.yaw if G.cam else 0.0
	map_rect.pivot_offset = map_rect.size * 0.5
	map_rect.rotation = deg_to_rad(cam_yaw)
	map_rect.position = (map_clip.size - map_rect.size) * 0.5 + off
	var heading: float = rad_to_deg((p.vehicle.rotation.y if p.vehicle else p.rotation.y))
	arrow.pivot_offset = arrow.size * 0.5
	arrow.rotation = deg_to_rad(cam_yaw - heading)
	var cs := cos(deg_to_rad(cam_yaw))
	var sn := sin(deg_to_rad(cam_yaw))
	var centre := map_clip.size * 0.5
	for b in blips:
		var dv := Vector2(b[1].x - pos.x, b[1].z - pos.z) * k
		var r := Vector2(dv.x * cs - dv.y * sn, dv.x * sn + dv.y * cs) + off
		r.x = clampf(r.x, -MAP_W / 2 + 14, MAP_W / 2 - 14)
		r.y = clampf(r.y, -MAP_H / 2 + 14, MAP_H / 2 - 14)
		b[0].position = centre + r - b[0].size * 0.5
	var n := 0
	if Wanted.stars > 0:
		for h in Human.all:
			if not h.police or h.dead or n >= cop_blips.size():
				continue
			var dv := Vector2(h.global_position.x - pos.x, h.global_position.z - pos.z) * k
			var r := Vector2(dv.x * cs - dv.y * sn, dv.x * sn + dv.y * cs) + off
			if absf(r.x) > MAP_W / 2 or absf(r.y) > MAP_H / 2:
				continue
			var im: Control = cop_blips[n]
			n += 1
			im.visible = true
			Ui.set_color(im, Color(0.3, 0.5, 1.0) if sin(real() * 8.0) > 0.0 else Color(1.0, 0.25, 0.25))
			im.position = centre + r - im.size * 0.5
	for i in range(n, cop_blips.size()):
		if cop_blips[i].visible:
			cop_blips[i].visible = false
