class_name Ui
extends RefCounted
## Builds the interface in code: boxes, pictures, text and buttons placed like the Unity version (anchor point,
## offset with y up, size in 1080p pixels), so the GTA-style layout carries over one to one.

const TL := Vector2(0, 1)
const TR := Vector2(1, 1)
const BL := Vector2(0, 0)
const BR := Vector2(1, 0)
const C := Vector2(0.5, 0.5)
const T := Vector2(0.5, 1)
const B := Vector2(0.5, 0)
const L := Vector2(0, 0.5)
const R := Vector2(1, 0.5)

static var font: Font
static var display: Font
static var title: Font
static var body: Font
static var _tex := {}
static var root: Control


static func init_fonts() -> void:
	font = _font("res://gen/fonts/UIFont.ttf")
	display = _font("res://gen/fonts/DisplayFont.ttf")
	title = _font("res://gen/fonts/TitleFont.otf")
	body = ThemeDB.fallback_font
	if font == null:
		font = body
	if display == null:
		display = font
	if title == null:
		title = display


static func _font(path: String) -> Font:
	return load(path) if ResourceLoader.exists(path) else null


static func tex(name: String) -> Texture2D:
	if name == "":
		return null
	if _tex.has(name):
		return _tex[name]
	var p := "res://gen/ui/%s.png" % name
	var t: Texture2D = load(p) if ResourceLoader.exists(p) else null
	_tex[name] = t
	return t


## Places 'c' with its pivot at 'anchor' (Unity style: y up) of the parent, offset by 'pos' (y up), sized 'size'.
static func place(c: Control, anchor: Vector2, pos: Vector2, size: Vector2) -> void:
	c.anchor_left = anchor.x
	c.anchor_right = anchor.x
	c.anchor_top = 1.0 - anchor.y
	c.anchor_bottom = 1.0 - anchor.y
	c.offset_left = pos.x - anchor.x * size.x
	c.offset_right = c.offset_left + size.x
	c.offset_top = -pos.y - (1.0 - anchor.y) * size.y
	c.offset_bottom = c.offset_top + size.y
	c.pivot_offset = Vector2(anchor.x * size.x, (1.0 - anchor.y) * size.y)


static func set_pos(c: Control, anchor: Vector2, pos: Vector2) -> void:
	var size := c.size
	c.offset_left = pos.x - anchor.x * size.x
	c.offset_right = c.offset_left + size.x
	c.offset_top = -pos.y - (1.0 - anchor.y) * size.y
	c.offset_bottom = c.offset_top + size.y


static func box(parent: Node, name: String, anchor: Vector2, pos: Vector2, size: Vector2) -> Control:
	var c := Control.new()
	c.name = name
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	place(c, anchor, pos, size)
	return c


static func fill(parent: Node, name: String, inset := 0.0) -> Control:
	var c := Control.new()
	c.name = name
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	c.offset_left = inset
	c.offset_top = inset
	c.offset_right = -inset
	c.offset_bottom = -inset
	return c


## A picture ('' = a plain colour box). 'panel' and 'pill' stretch like nine-patches.
static func img(parent: Node, sprite: String, col: Color, anchor: Vector2, pos: Vector2, size: Vector2) -> Control:
	var c: Control
	if sprite == "":
		var cr := ColorRect.new()
		cr.color = col
		c = cr
	elif sprite == "panel" or sprite == "pill":
		var np := NinePatchRect.new()
		np.texture = tex(sprite)
		var m := 36 if sprite == "panel" else 60
		if np.texture:
			m = mini(m, int(np.texture.get_width() / 2.0) - 1)
		np.patch_margin_left = m
		np.patch_margin_right = m
		np.patch_margin_top = m
		np.patch_margin_bottom = m
		np.self_modulate = col
		c = np
	else:
		var tr := TextureRect.new()
		tr.texture = tex(sprite)
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_SCALE
		tr.self_modulate = col
		c = tr
	c.name = sprite if sprite != "" else "img"
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	place(c, anchor, pos, size)
	return c


static func set_color(c: Control, col: Color) -> void:
	if c is ColorRect:
		c.color = col
	else:
		c.self_modulate = col


static func set_sprite(c: Control, sprite: String) -> void:
	if c is TextureRect:
		var t := tex(sprite)
		if c.texture != t:
			c.texture = t


static func txt(parent: Node, s: String, size: int, col: Color, align: String, anchor: Vector2, pos: Vector2, area: Vector2,
		f: Font = null, outline := true) -> Label:
	var l := Label.new()
	l.text = s
	var ls := LabelSettings.new()
	ls.font = f if f else font
	ls.font_size = size
	ls.font_color = col
	if outline:
		ls.outline_size = maxi(4, int(size / 9.0))
		ls.outline_color = Color(0, 0, 0, 0.85)
		ls.shadow_size = 0
	l.label_settings = ls
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.clip_text = false
	match align:
		"left":
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		"right":
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		"upper_left":
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
			l.vertical_alignment = VERTICAL_ALIGNMENT_TOP
		"lower_right":
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			l.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		_:
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	parent.add_child(l)
	place(l, anchor, pos, area)
	return l


static func txt_color(l: Label, c: Color) -> void:
	l.label_settings.font_color = c


## Width of a label's text in pixels.
static func text_width(l: Label) -> float:
	var ls := l.label_settings
	return ls.font.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, ls.font_size).x


## A round, domed button (tinted) with a white icon and an optional label under it.
static func round_btn(parent: Node, icon: String, label: String, col: Color, anchor: Vector2, pos: Vector2, size: float,
		click: Callable = Callable()) -> HoldBtn:
	var glass := col.r > 0.9 and col.g > 0.9 and col.b > 0.9
	var b := HoldBtn.new()
	b.name = "btn_" + (icon if icon != "" else label)
	parent.add_child(b)
	place(b, anchor, pos, Vector2(size, size))
	b.bg = img(b, "btn_round" if glass else "btn_light", col, C, Vector2.ZERO, Vector2(size, size))
	b.base_color = col
	b.on_click = click
	if icon != "":
		b.icon = img(b, "i_" + icon, Color.WHITE, C, Vector2.ZERO, Vector2(size * 0.56, size * 0.56))
	if label != "":
		b.label = txt(b, label, int(size * (0.2 if icon != "" else 0.3)), Color.WHITE, "center", B if icon != "" else C,
			Vector2(0, -size * 0.2) if icon != "" else Vector2.ZERO, Vector2(size * 1.6, size * 0.4))
	return b


## A wide rounded button with text (menus, shops).
static func wide(parent: Node, label: String, col: Color, anchor: Vector2, pos: Vector2, size: Vector2, click: Callable,
		font_size := 0) -> HoldBtn:
	var b := HoldBtn.new()
	b.name = "btn_" + label
	parent.add_child(b)
	place(b, anchor, pos, size)
	b.bg = img(b, "", col, C, Vector2.ZERO, size)
	b.base_color = col
	b.on_click = click
	b.label = txt(b, label, font_size if font_size > 0 else int(size.y * 0.5), Color.WHITE, "center", C, Vector2(0, 2), size)
	return b


static func clear(n: Node) -> void:
	for c in n.get_children():
		c.queue_free()
