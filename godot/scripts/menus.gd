class_name Menus
extends Control
## Main menu, pause, settings, credits, the gun shop, the clothes shop, the house, the phone and the big map.

static var I: Menus

const OUTFITS := ["player_casual", "player_kurta", "player_jacket"]
const OUTFIT_NAMES := ["CASUAL", "KURTA", "JACKET"]
const OUTFIT_PRICE := [0, 3000, 6000]
const TINTS := [Color(1, 1, 1), Color(1.0, 0.78, 0.75), Color(0.75, 0.85, 1.0), Color(0.78, 1.0, 0.8), Color(1.0, 0.95, 0.7), Color(0.62, 0.62, 0.66)]

var current: Control = null
var current_name := ""
var dial := ""
var dial_text: Label


static func create(parent: Control) -> Menus:
	var m := Menus.new()
	m.name = "Menus"
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.process_mode = Node.PROCESS_MODE_ALWAYS
	parent.add_child(m)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	I = m
	G.menus = m
	return m


func is_open() -> bool:
	return current != null


func close() -> void:
	if current:
		current.queue_free()
	current = null
	current_name = ""
	if G.game and G.game.state == G.game.S.PAUSED:
		G.game.resume()


func _blocker(name: String, col: Color) -> Control:
	if current:
		current.queue_free()
	current_name = name
	var bg := ColorRect.new()
	bg.name = name
	bg.color = col
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	current = bg
	return bg


func window(name: String, title: String, size: Vector2, closable := true, dim := true) -> Control:
	var bg := _blocker(name, Color(0, 0, 0, 0.6) if dim else Color(0, 0, 0, 0))
	var panel := Ui.img(bg, "", Color(0.03, 0.03, 0.04, 0.9), Ui.C, Vector2.ZERO, size)
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	if title != "":
		var band := Ui.img(panel, "", Color(0, 0, 0, 0.95), Ui.T, Vector2.ZERO, Vector2(size.x, 100))
		Ui.txt(band, title, 70, Color.WHITE, "left", Ui.L, Vector2(40, 0), Vector2(size.x - 200, 100), Ui.title)
	if closable:
		Ui.round_btn(panel, "exit", "", Color.WHITE, Ui.TR, Vector2(-14, -10), 80, close)
	return panel


## A GTA-style menu line: white text on dark glass, lights up while pressed.
func item(parent: Node, label: String, anchor: Vector2, pos: Vector2, size: Vector2, click: Callable, font_size := 46) -> HoldBtn:
	var b := Ui.wide(parent, label, Color(0, 0, 0, 0.45), anchor, pos, size, click, font_size)
	b.label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	Ui.place(b.label, Ui.C, Vector2.ZERO, Vector2(size.x - 60, size.y))
	return b


func scroll(parent: Node, pos: Vector2, size: Vector2) -> VBoxContainer:
	var sc := ScrollContainer.new()
	sc.name = "scroll"
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	parent.add_child(sc)
	Ui.place(sc, Ui.T, pos, size)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	v.custom_minimum_size = Vector2(size.x, 0)
	v.mouse_filter = Control.MOUSE_FILTER_PASS
	sc.add_child(v)
	return v


func row(list: VBoxContainer, w: float, h: float) -> Control:
	var r := Control.new()
	r.custom_minimum_size = Vector2(w, h)
	r.mouse_filter = Control.MOUSE_FILTER_PASS
	list.add_child(r)
	var bg := Ui.img(r, "panel", Color(1, 1, 1, 0.08), Ui.C, Vector2.ZERO, Vector2(w, h))
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return r


# ------------------------------------------------------------------ main menu
func main_menu() -> void:
	var bg := _blocker("main", Color(0, 0, 0, 0.12))
	var side := ColorRect.new()
	side.color = Color(0, 0, 0, 0.55)
	side.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bg.add_child(side)
	side.anchor_left = 0
	side.anchor_right = 0
	side.anchor_top = 0
	side.anchor_bottom = 1
	side.offset_right = 720
	Ui.txt(bg, "DANGA", 200, Color.WHITE, "left", Ui.TL, Vector2(70, -30), Vector2(900, 240), Ui.title)
	Ui.txt(bg, "AGARTALA • TRIPURA", 40, Color(1, 1, 1, 0.8), "left", Ui.TL, Vector2(84, -262), Vector2(800, 50))
	var has_save := Save.exists()
	var y := -360.0
	if has_save:
		item(bg, "CONTINUE", Ui.TL, Vector2(70, y), Vector2(560, 84), func(): G.game.play(true))
		y -= 100
	item(bg, "NEW GAME" if has_save else "PLAY", Ui.TL, Vector2(70, y), Vector2(560, 84), func(): G.game.play(false))
	y -= 100
	item(bg, "SETTINGS", Ui.TL, Vector2(70, y), Vector2(560, 84), func(): settings(main_menu))
	y -= 100
	item(bg, "CREDITS", Ui.TL, Vector2(70, y), Vector2(560, 84), credits)
	Ui.txt(bg, "MXYAN GAMES OFFICIAL", 34, Color(1, 1, 1, 0.85), "left", Ui.BL, Vector2(80, 40), Vector2(700, 50))
	Ui.txt(bg, "v" + ProjectSettings.get_setting("application/config/version", "2.0"), 26, Color(1, 1, 1, 0.6), "right", Ui.BR, Vector2(-30, 30), Vector2(300, 40))


func credits() -> void:
	var w := window("credits", "CREDITS", Vector2(1500, 900))
	var list := scroll(w, Vector2(0, -110), Vector2(1400, 760))
	var txt := "DANGA\nMade by MXYAN GAMES\n\n"
	if FileAccess.file_exists("res://gen/CREDITS.txt"):
		txt += FileAccess.get_file_as_string("res://gen/CREDITS.txt")
	for para in txt.split("\n\n", false):
		var l := Label.new()
		l.text = para.strip_edges()
		var ls := LabelSettings.new()
		ls.font = Ui.font
		ls.font_size = 26
		l.label_settings = ls
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size = Vector2(1360, 0)
		l.mouse_filter = Control.MOUSE_FILTER_PASS
		list.add_child(l)
	Ui.wide(w, "BACK", G.SAFFRON, Ui.B, Vector2(0, -50), Vector2(300, 90), func():
		if G.game.state == G.game.S.MENU:
			main_menu()
		else:
			pause())


# ------------------------------------------------------------------ pause and settings
func pause() -> void:
	if G.game.state != G.game.S.PLAY and G.game.state != G.game.S.PAUSED:
		return
	G.game.pause_game()
	var w := window("pause", "PAUSED", Vector2(760, 820))
	var y := -150.0
	item(w, "RESUME", Ui.T, Vector2(0, y), Vector2(600, 96), close, 52)
	y -= 116
	item(w, "MAP", Ui.T, Vector2(0, y), Vector2(600, 96), big_map, 52)
	y -= 116
	item(w, "SETTINGS", Ui.T, Vector2(0, y), Vector2(600, 96), func(): settings(pause), 52)
	y -= 116
	item(w, "CREDITS", Ui.T, Vector2(0, y), Vector2(600, 96), credits, 52)
	y -= 116
	item(w, "QUIT TO MAIN MENU", Ui.T, Vector2(0, y), Vector2(600, 96), func():
		close()
		G.game.to_menu(), 52)


func settings(back: Callable) -> void:
	if G.game.state == G.game.S.PLAY:
		G.game.pause_game()
	var w := window("settings", "SETTINGS", Vector2(1300, 900), false)
	var st: Dictionary = G.game.settings
	var list := scroll(w, Vector2(0, -120), Vector2(1200, 640))
	option(list, "GRAPHICS", ["LOW", "MEDIUM", "HIGH"], st, "quality")
	option(list, "DRAW DISTANCE", ["NEAR", "NORMAL", "FAR"], st, "distance")
	option(list, "TRAFFIC & PEOPLE", ["FEW", "NORMAL", "MANY"], st, "density")
	option(list, "SOUND", _numbers(), st, "sound")
	option(list, "MUSIC & RADIO", _numbers(), st, "music")
	option(list, "CAMERA SPEED", _numbers(), st, "sens")
	option(list, "SHOW FPS", ["OFF", "ON"], st, "fps")
	Ui.wide(w, "DONE", G.GREEN, Ui.B, Vector2(0, -50), Vector2(340, 100), func():
		G.game.save_settings()
		back.call())


static func _numbers() -> Array:
	var a := []
	for i in 11:
		a.append(str(i))
	return a


func option(list: VBoxContainer, label: String, values: Array, st: Dictionary, key: String) -> void:
	var r := row(list, 1160, 110)
	Ui.txt(r, label, 46, Color.WHITE, "left", Ui.L, Vector2(30, 0), Vector2(560, 100))
	var val := Ui.txt(r, values[clampi(st[key], 0, values.size() - 1)], 50, G.YELLOW, "center", Ui.R, Vector2(-150, 0), Vector2(260, 100))
	var refresh := func(): val.text = values[clampi(st[key], 0, values.size() - 1)]
	Ui.round_btn(r, "left", "", G.SAFFRON, Ui.R, Vector2(-420, 0), 86, func():
		st[key] = maxi(0, st[key] - 1)
		G.game.apply_settings()
		refresh.call())
	Ui.round_btn(r, "right", "", G.SAFFRON, Ui.R, Vector2(-30, 0), 86, func():
		st[key] = mini(values.size() - 1, st[key] + 1)
		G.game.apply_settings()
		refresh.call())


# ------------------------------------------------------------------ shops and the house
func gun_shop() -> void:
	G.game.pause_game()
	var w := window("gunshop", "DANGA ARMS", Vector2(1500, 920))
	fill_shop(w)


func fill_shop(w: Control) -> void:
	var p := Player.I
	for n in ["scroll", "cash"]:
		var old := w.get_node_or_null(n)
		if old:
			old.name = n + "_old"
			old.queue_free()
	var ct := Ui.txt(w, "₹ " + G.rupees(p.money), 56, G.MONEY, "right", Ui.TR, Vector2(-120, 0), Vector2(600, 100), Ui.font)
	ct.name = "cash"
	var list := scroll(w, Vector2(0, -120), Vector2(1400, 760))
	for d in Combat.DEFS:
		if d["id"] == Combat.FIST:
			continue
		var r := row(list, 1360, 130)
		Ui.img(r, "i_" + d["icon"], Color.WHITE, Ui.L, Vector2(30, 0), Vector2(100, 100))
		Ui.txt(r, d["name"].to_upper(), 50, Color.WHITE, "left", Ui.L, Vector2(160, 18), Vector2(520, 60))
		var info := ("MELEE  •  DAMAGE %d" % int(d["damage"])) if d["melee"] else ("DAMAGE %d  •  MAG %d  •  AMMO %d" % [int(d["damage"] * d["pellets"]), d["mag"], p.total_ammo(d["id"])])
		Ui.txt(r, info, 30, Color(1, 1, 1, 0.7), "left", Ui.L, Vector2(160, -30), Vector2(700, 40))
		var own: bool = p.owned.has(d["id"])
		var def: Dictionary = d
		if not own:
			Ui.wide(r, "BUY ₹" + G.rupees(d["price"]), G.GREEN if p.money >= d["price"] else Color(0.4, 0.4, 0.4), Ui.R, Vector2(-30, 0), Vector2(380, 90), func():
				if p.money < def["price"]:
					Hud.toast("Not enough money", G.RED)
					return
				p.money -= def["price"]
				p.owned[def["id"]] = true
				if not def["melee"]:
					p.clip[def["id"]] = def["mag"]
					p.ammo[def["id"]] = def["ammo_pack"]
				p.equip(def["id"])
				G.audio.ui("cash", 0.8)
				fill_shop(w), 40)
		elif not d["melee"]:
			Ui.wide(r, "+%d AMMO ₹%s" % [d["ammo_pack"], G.rupees(d["ammo_price"])], G.BLUE if p.money >= d["ammo_price"] else Color(0.4, 0.4, 0.4), Ui.R, Vector2(-30, 0), Vector2(440, 90), func():
				if p.money < def["ammo_price"]:
					Hud.toast("Not enough money", G.RED)
					return
				p.money -= def["ammo_price"]
				p.ammo[def["id"]] += def["ammo_pack"]
				G.audio.ui("reload", 0.8)
				fill_shop(w), 36)
		else:
			Ui.txt(r, "OWNED", 46, G.GREEN, "right", Ui.R, Vector2(-40, 0), Vector2(300, 90))
	var ar := row(list, 1360, 130)
	Ui.img(ar, "i_shield", Color(0.5, 0.75, 1.0), Ui.L, Vector2(30, 0), Vector2(100, 100))
	Ui.txt(ar, "BODY ARMOUR", 50, Color.WHITE, "left", Ui.L, Vector2(160, 0), Vector2(520, 60))
	Ui.wide(ar, "BUY ₹2,500", G.GREEN if p.money >= 2500 else Color(0.4, 0.4, 0.4), Ui.R, Vector2(-30, 0), Vector2(380, 90), func():
		if p.money < 2500:
			Hud.toast("Not enough money", G.RED)
			return
		p.money -= 2500
		p.armor = 100.0
		G.audio.ui("cash", 0.8)
		fill_shop(w), 40)


func clothes(wardrobe: bool) -> void:
	G.game.pause_game()
	var w := window("clothes", "WARDROBE" if wardrobe else "FASHION POINT", Vector2(1500, 900))
	var p := Player.I
	var st: Dictionary = G.game.save
	var x := -460.0
	for i in OUTFITS.size():
		var k := i
		var own: bool = st["outfits"].has(OUTFITS[i]) or OUTFIT_PRICE[i] == 0
		if wardrobe and not own:
			continue
		var card := Ui.img(w, "panel", Color(1.0, 0.6, 0.1, 0.35) if p.outfit == OUTFITS[i] else Color(1, 1, 1, 0.08), Ui.C, Vector2(x, 60), Vector2(400, 460))
		Ui.img(card, "i_shirt", Color.WHITE, Ui.T, Vector2(0, -40), Vector2(200, 200))
		Ui.txt(card, OUTFIT_NAMES[i], 58, Color.WHITE, "center", Ui.C, Vector2(0, -60), Vector2(380, 80))
		var lbl := "WEARING" if p.outfit == OUTFITS[i] else ("WEAR" if own else "BUY ₹" + G.rupees(OUTFIT_PRICE[i]))
		Ui.wide(card, lbl, G.GREEN if own else G.SAFFRON, Ui.B, Vector2(0, 30), Vector2(330, 90), func():
			if not own:
				if p.money < OUTFIT_PRICE[k]:
					Hud.toast("Not enough money", G.RED)
					return
				p.money -= OUTFIT_PRICE[k]
				st["outfits"].append(OUTFITS[k])
				G.audio.ui("cash", 0.8)
			p.set_outfit(OUTFITS[k], p.tint)
			clothes(wardrobe), 40)
		x += 460.0
	Ui.txt(w, "COLOUR", 44, Color.WHITE, "left", Ui.B, Vector2(-560, 120), Vector2(300, 60))
	for i in TINTS.size():
		var c: Color = TINTS[i]
		Ui.round_btn(w, "", "", c, Ui.B, Vector2(-330 + i * 130, 120), 100, func(): p.set_outfit(p.outfit, c))


func house() -> void:
	G.game.pause_game()
	var w := window("house", "YOUR HOUSE", Vector2(900, 760))
	Ui.wide(w, "SAVE GAME", G.GREEN, Ui.T, Vector2(0, -160), Vector2(560, 110), func():
		G.game.save_game()
		Hud.toast("Game saved", G.GREEN)
		close())
	Ui.wide(w, "SLEEP 6 HOURS", G.BLUE, Ui.T, Vector2(0, -300), Vector2(560, 110), func():
		G.env.hour = fposmod(G.env.hour + 6.0, 24.0)
		Player.I.health = Player.I.max_health
		Wanted.set_stars(0)
		G.game.save_game()
		Hud.toast("You slept. It is " + G.env.clock() + " now.", Color.WHITE, 3.0)
		close())
	Ui.wide(w, "WARDROBE", G.SAFFRON, Ui.T, Vector2(0, -440), Vector2(560, 110), func(): clothes(true))
	Ui.txt(w, "Your motorbike is parked outside.", 30, Color(1, 1, 1, 0.75), "center", Ui.B, Vector2(0, 60), Vector2(800, 50), Ui.font, false)


# ------------------------------------------------------------------ the phone
func phone() -> void:
	if G.game.state != G.game.S.PLAY:
		return
	G.game.pause_game()
	G.audio.ui("phone_ring", 0.25)
	phone_home()


func phone_frame(app: String) -> Control:
	var bg := _blocker("phone", Color(0, 0, 0, 0.4))
	var body := Ui.img(bg, "panel", Color(0.05, 0.05, 0.06, 1.0), Ui.R, Vector2(-160, -20), Vector2(560, 980))
	body.mouse_filter = Control.MOUSE_FILTER_STOP
	var screen := Ui.img(body, "panel", Color(0.12, 0.16, 0.24, 1.0), Ui.C, Vector2(0, 20), Vector2(500, 840))
	Ui.txt(screen, G.env.clock(), 34, Color.WHITE, "left", Ui.TL, Vector2(24, -10), Vector2(200, 44), Ui.font, false)
	Ui.txt(screen, app, 34, Color.WHITE, "right", Ui.TR, Vector2(-24, -10), Vector2(300, 44), Ui.font, false)
	Ui.round_btn(body, "", "", Color(0.25, 0.25, 0.28), Ui.B, Vector2(0, 14), 76, func():
		if app == "DANGA":
			close()
		else:
			phone_home())
	return screen


func phone_home() -> void:
	var s := phone_frame("DANGA")
	var apps := ["dial", "map", "wallet", "radio", "notes", "settings"]
	var names := ["CHEATS", "MAP", "WALLET", "RADIO", "NOTES", "SETTINGS"]
	var cols := [G.GREEN, G.BLUE, Color(0.2, 0.6, 0.3), G.SAFFRON, G.YELLOW, Color(0.45, 0.45, 0.5)]
	for i in apps.size():
		var k := i
		var b := Ui.round_btn(s, apps[i], "", cols[i], Ui.T, Vector2(-150 + (i % 3) * 150, -110 - (i / 3) * 210), 120, func(): app(apps[k]))
		Ui.txt(b, names[i], 26, Color.WHITE, "center", Ui.B, Vector2(0, -44), Vector2(160, 40))
	Ui.txt(s, "MXYAN GAMES OFFICIAL", 22, Color(1, 1, 1, 0.5), "center", Ui.B, Vector2(0, 30), Vector2(460, 40), Ui.font, false)


func app(a: String) -> void:
	match a:
		"dial":
			dialer()
		"map":
			big_map()
		"wallet":
			wallet()
		"radio":
			radio_app()
		"notes":
			notes()
		"settings":
			settings(phone_home)


func dialer() -> void:
	var s := phone_frame("CHEATS")
	dial = ""
	var disp := Ui.img(s, "pill", Color(0, 0, 0, 0.5), Ui.T, Vector2(0, -70), Vector2(440, 100))
	dial_text = Ui.txt(disp, "", 60, Color.WHITE, "center", Ui.C, Vector2.ZERO, Vector2(420, 90), Ui.font, false)
	var keys := ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
	for i in keys.size():
		var k: String = keys[i]
		Ui.round_btn(s, "", k, Color(0.25, 0.28, 0.36), Ui.T, Vector2(-140 + (i % 3) * 140, -200 - (i / 3) * 130), 112, func():
			if dial.length() < 8:
				dial += k
			dial_text.text = dial
			dial_text.label_settings.font_size = 60
			Ui.txt_color(dial_text, Color.WHITE))
	Ui.round_btn(s, "phone", "", G.GREEN, Ui.B, Vector2(-70, 40), 120, func():
		var msg: String = G.game.cheat(dial)
		dial_text.text = msg if msg != "" else "WRONG NUMBER"
		Ui.txt_color(dial_text, G.GREEN if msg != "" else G.RED)
		dial_text.label_settings.font_size = 34 if msg != "" else 44
		dial = "")
	Ui.round_btn(s, "left", "", G.RED, Ui.B, Vector2(80, 40), 100, func():
		if dial.length() > 0:
			dial = dial.substr(0, dial.length() - 1)
		dial_text.text = dial
		dial_text.label_settings.font_size = 60)


func wallet() -> void:
	var s := phone_frame("WALLET")
	var p := Player.I
	Ui.img(s, "i_rupee", Color(0.6, 1.0, 0.55), Ui.T, Vector2(0, -80), Vector2(110, 110))
	Ui.txt(s, G.rupees(p.money), 70, Color(0.6, 1.0, 0.55), "center", Ui.T, Vector2(0, -200), Vector2(480, 90), Ui.display)
	var y := -300.0
	for d in Combat.DEFS:
		if not p.owned.has(d["id"]) or d["id"] == Combat.FIST:
			continue
		Ui.img(s, "i_" + d["icon"], Color.WHITE, Ui.TL, Vector2(40, y), Vector2(64, 64))
		Ui.txt(s, d["name"].to_upper() + ("" if d["melee"] else "   %d" % p.total_ammo(d["id"])), 34, Color.WHITE, "left", Ui.TL, Vector2(120, y - 6), Vector2(360, 56))
		y -= 76


func radio_app() -> void:
	var s := phone_frame("RADIO")
	var a: GameAudio = G.audio
	for i in GameAudio.STATIONS.size():
		var k := i
		var on := a.station == i
		Ui.wide(s, GameAudio.STATION_NAMES[i].to_upper(), G.SAFFRON if on else Color(0.25, 0.28, 0.36), Ui.T, Vector2(0, -90 - i * 120), Vector2(450, 100), func():
			a.station = k
			G.game.save["station"] = k
			a.radio_on(Player.I.vehicle != null)
			radio_app(), 26)
	Ui.wide(s, "RADIO OFF", G.RED if a.station < 0 else Color(0.25, 0.28, 0.36), Ui.T, Vector2(0, -90 - GameAudio.STATIONS.size() * 120), Vector2(450, 100), func():
		a.station = -1
		G.game.save["station"] = -1
		a.radio_on(false)
		radio_app(), 30)
	Ui.txt(s, "The radio plays while you drive.", 26, Color(1, 1, 1, 0.6), "center", Ui.B, Vector2(0, 40), Vector2(460, 40), Ui.font, false)


func notes() -> void:
	var s := phone_frame("NOTES")
	var list := scroll(s, Vector2(0, -60), Vector2(470, 760))
	var l := Label.new()
	l.text = Game.CHEAT_LIST
	var ls := LabelSettings.new()
	ls.font = Ui.font
	ls.font_size = 28
	l.label_settings = ls
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(440, 0)
	list.add_child(l)


# ------------------------------------------------------------------ the big map
func big_map() -> void:
	if G.game.state == G.game.S.PLAY:
		G.game.pause_game()
	var w := window("map", "", Vector2(1900, 1060))
	var m := TextureRect.new()
	m.name = "map"
	m.texture = load("res://gen/city/map.png") if ResourceLoader.exists("res://gen/city/map.png") else null
	m.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	m.stretch_mode = TextureRect.STRETCH_SCALE
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	w.add_child(m)
	Ui.place(m, Ui.L, Vector2(30, 0), Vector2(1000, 1000))
	var H: float = G.city.half
	var k := 1000.0 / (2.0 * H)
	var used: Array[Rect2] = []
	var names: Array = []
	for p in G.city.points:
		var icon := ""
		var c := Color.WHITE
		match p["kind"]:
			"house":
				icon = "house"
				c = G.GREEN
			"gunshop":
				icon = "pistol"
				c = G.RED
			"clothes":
				icon = "shirt"
				c = Color(0.85, 0.5, 1.0)
			"hospital":
				icon = "cross"
				c = G.RED
			"police":
				icon = "badge"
				c = G.BLUE
			"boat":
				icon = "boat"
				c = Color(0.4, 0.85, 1.0)
			"vehicle":
				if p["model"] == "helicopter":
					icon = "heli"
					c = G.YELLOW
		var pos := Vector2((p["p"].x + H) * k, (p["p"].z + H) * k)        # top-left origin, north up
		if icon != "":
			var bg := Ui.img(m, "mask_circle", Color(0, 0, 0, 0.8), Ui.TL, Vector2(pos.x, -pos.y) + Vector2(-22, 22), Vector2(44, 44))
			Ui.img(bg, "i_" + icon, c, Ui.C, Vector2.ZERO, Vector2(30, 30))
			used.append(Rect2(pos.x - 22, pos.y - 22, 44, 44))
		elif p["kind"] == "landmark" and p["label"] != "":
			names.append(p)
	var tries := [Vector2.ZERO, Vector2(0, -26), Vector2(0, 26), Vector2(0, -50), Vector2(0, 50)]
	for p in names:
		var label: String = p["label"].split("(")[0].strip_edges()
		var tw := label.length() * 10.5 + 12.0
		var base := Vector2((p["p"].x + H) * k, (p["p"].z + H) * k)
		for off in tries:
			var q: Vector2 = base + off
			q.x = clampf(q.x, tw * 0.5, 1000.0 - tw * 0.5)
			var r := Rect2(q.x - tw * 0.5, q.y - 13.0, tw, 26.0)
			if q.y < 14.0 or q.y > 986.0 or used.any(func(o): return o.intersects(r)):
				continue
			used.append(r)
			Ui.txt(m, label, 20, Color.WHITE, "center", Ui.TL, Vector2(q.x - (tw + 20.0) * 0.5, -(q.y - 15.0)), Vector2(tw + 20.0, 30), Ui.font, true)
			break
	var pl := Player.I
	var pp: Vector3 = pl.vehicle.global_position if pl.vehicle else pl.global_position
	var apos := Vector2((pp.x + H) * k, (pp.z + H) * k)
	var ar := Ui.img(m, "arrow", G.YELLOW, Ui.TL, Vector2(apos.x - 23, -(apos.y - 23)), Vector2(46, 46))
	ar.pivot_offset = Vector2(23, 23)
	ar.rotation = -(pl.vehicle.rotation.y if pl.vehicle else pl.rotation.y)
	Ui.txt(w, "AGARTALA", 90, Color.WHITE, "left", Ui.TL, Vector2(1080, -60), Vector2(760, 120), Ui.display)
	Ui.txt(w, "You are in " + G.city.zone_at(pp), 40, G.YELLOW, "left", Ui.TL, Vector2(1080, -170), Vector2(760, 60), Ui.font)
	var leg := ["house|Your house", "pistol|Danga Arms - guns", "shirt|Fashion Point - clothes", "cross|Hospital", "badge|Police station", "boat|Boat jetty", "heli|Helicopter"]
	for i in leg.size():
		var parts: PackedStringArray = leg[i].split("|")
		Ui.img(w, "i_" + parts[0], Color.WHITE, Ui.TL, Vector2(1090, -260 - i * 76), Vector2(56, 56))
		Ui.txt(w, parts[1], 36, Color.WHITE, "left", Ui.TL, Vector2(1170, -262 - i * 76), Vector2(640, 60), Ui.font)
