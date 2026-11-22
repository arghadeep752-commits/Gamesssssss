"""Texture layers for the map (one 1024 x 1024 picture per layer, in mesh.LAYERS order), the minimap picture and the
ground light map (soft contact shadows and sun shadows of buildings and trees, baked from the layout).

Photo layers come from the downloaded CC0 scans (tools/fetch_assets.py). The rest are composed from those photos
(windows, shop shutters, paddy fields, leaf cards) or drawn (road paint, sign boards with the dafont fonts)."""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import layout as LY
from mesh import LAYERS

SIZE = 1024
PHOTO = {"asphalt", "asphalt_old", "paving", "curb", "concrete", "plaster", "plaster_old", "brick", "roof_tin", "roof_tiles", "grass",
         "ground", "sand", "rock", "wood", "metal", "marble", "tiles", "bark", "fabric", "facade1", "facade2"}
SHOP_SIGNS = ["MAA TRIPURESWARI STORES", "AGARTALA SWEETS", "BHAI BHAI HARDWARE", "NEW SAHA MEDICAL", "BABU TELECOM", "DAS CLOTH HOUSE",
              "RAJ HOTEL & RESTAURANT", "SARKAR ELECTRONICS", "TRIPURA TAILORS", "MOMO CORNER", "GHOSH JEWELLERS", "ROY PHARMACY",
              "DANGA ARMS", "FASHION POINT", "HOSPITAL", "POLICE STATION"]
SIGNS2 = [("AGARTALA", 8.3), ("MAHARAJA BIR BIKRAM AIRPORT", 19), ("INDIA", 7.3), ("CITY CENTRE", 24), ("UJJAYANTA PALACE", 10),
          ("TRIPURA STATE MUSEUM", 10), ("MBB COLLEGE", 10), ("HERITAGE PARK", 7), ("AGARTALA HARBOUR", 16), ("WELCOME TO AGARTALA", 12),
          ("BATTALA BAZAAR", 16.7), ("MOTOR STAND", 13), ("RABINDRA KANAN", 7), ("NEERMAHAL", 8), ("TRIPURA SUNDARI MANDIR", 12),
          ("GEDU MIA MASJID", 16.7)]
SIGN_ASPECT = {"DANGA ARMS": 6.3, "FASHION POINT": 5.6, "HOSPITAL": 28, "POLICE STATION": 11.9}
BOARD = [((200, 30, 30), (255, 240, 200)), ((20, 60, 160), (255, 255, 255)), ((250, 200, 20), (120, 10, 10)), ((30, 120, 50), (255, 255, 255)),
         ((245, 245, 240), (190, 20, 20)), ((20, 20, 25), (255, 210, 60)), ((230, 90, 20), (255, 255, 255)), ((90, 20, 120), (255, 230, 120))]


def _load(path, mode="RGB"):
    im = Image.open(path)
    if im.mode in ("I;16", "I"):
        a = np.asarray(im, np.float32)
        a = a / max(1.0, a.max()) * 255.0
        im = Image.fromarray(a.astype(np.uint8), "L")
    return im.convert(mode).resize((SIZE, SIZE), Image.LANCZOS)


def _font(fonts_dir, role, size):
    for ext in (".ttf", ".otf"):
        p = os.path.join(fonts_dir, role + ext)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:       # noqa: BLE001
                pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except Exception:       # noqa: BLE001
        return ImageFont.load_default()


def noise(shape, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, shape[0] // scale), max(2, shape[1] // scale)))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255.0


# ------------------------------------------------------------------------------------------------ composed layers
def window_layer(tex):
    wood = np.asarray(_load(os.path.join(tex, "wood", "diff.jpg")), np.float32) / 255
    metal = np.asarray(_load(os.path.join(tex, "metal", "diff.jpg")), np.float32) / 255
    fabric = np.asarray(_load(os.path.join(tex, "fabric", "diff.jpg")), np.float32) / 255
    out = np.zeros((SIZE, SIZE, 3), np.float32)
    W, H = 512, 470          # natural window proportions, squeezed into a 256 x 1024 strip
    for v in range(4):
        img = np.zeros((H, W, 3), np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        # glass: sky reflection gradient
        g = np.stack([0.18 + 0.25 * (1 - yy / H), 0.22 + 0.28 * (1 - yy / H), 0.28 + 0.3 * (1 - yy / H)], -1)
        streak = (np.abs(((xx + yy * 0.6) % 180) - 60) < 18) * 0.08
        img = g + streak[..., None]
        frame_col = [wood[:H, :W] * np.array([0.9, 0.75, 0.6]), metal[:H, :W] * 0 + np.array([0.75, 0.76, 0.78]),
                     wood[:H, :W] * np.array([0.35, 0.6, 0.45]), wood[:H, :W] * np.array([0.95, 0.95, 0.92])][v]
        t = 26
        frame = (xx < t) | (xx > W - t) | (yy < t) | (yy > H - t) | (np.abs(xx - W / 2) < t / 2)
        if v == 2:      # closed wooden shutters
            img = wood[:H, :W] * np.array([0.35, 0.62, 0.5])
            slats = ((yy // 18) % 2 == 0)
            img = img * np.where(slats[..., None], 1.0, 0.82)
        if v == 3:      # curtains behind the glass
            cur = fabric[:H, :W] * np.array([1.0, 0.75, 0.55])
            mask = (np.abs(xx - W / 2) > W * 0.22)[..., None]
            img = np.where(mask, cur * 0.9, img)
        img = np.where(frame[..., None], frame_col, img)
        # iron grill (most Indian windows have one)
        if v in (0, 3):
            bars = ((xx % 46) < 7) & ~frame
            img = np.where(bars[..., None], np.array([0.12, 0.12, 0.13]), img)
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((256, SIZE), Image.LANCZOS)
        out[:, v * 256:(v + 1) * 256] = np.asarray(im, np.float32) / 255
    return out


def shopfront_layer(tex):
    tin = np.asarray(_load(os.path.join(tex, "roof_tin", "diff.jpg")).rotate(90), np.float32) / 255
    W, H = 600, 520
    # rolling shutter
    yy, xx = np.mgrid[0:H, 0:W]
    sh = tin[:H, :W] * np.array([0.8, 0.82, 0.85])
    ribs = 0.85 + 0.15 * np.sin(yy / 4.0)
    sh = sh * ribs[..., None]
    sh[H - 30:] *= 0.6
    left = Image.fromarray((np.clip(sh, 0, 1) * 255).astype(np.uint8)).resize((512, SIZE), Image.LANCZOS)
    # open shop: dark interior, shelves of colourful goods, a counter
    rnd = random.Random(4)
    im = Image.new("RGB", (W, H), (40, 34, 30))
    d = ImageDraw.Draw(im)
    for row in range(5):
        y0 = 40 + row * 70
        d.rectangle([20, y0 + 50, W - 20, y0 + 56], fill=(90, 70, 50))
        x = 24
        while x < W - 40:
            w = rnd.randint(14, 34)
            h = rnd.randint(22, 48)
            c = tuple(rnd.randint(60, 240) for _ in range(3))
            d.rectangle([x, y0 + 50 - h, x + w, y0 + 50], fill=c)
            x += w + rnd.randint(2, 6)
    d.rectangle([0, H - 120, W, H], fill=(120, 90, 60))
    d.rectangle([0, H - 120, W, H - 110], fill=(170, 130, 90))
    lights = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(lights).ellipse([W / 2 - 120, -60, W / 2 + 120, 120], fill=(80, 70, 40))
    im = Image.fromarray(np.clip(np.asarray(im, np.int32) + np.asarray(lights.filter(ImageFilter.GaussianBlur(40)), np.int32), 0, 255).astype(np.uint8))
    right = im.resize((512, SIZE), Image.LANCZOS)
    out = Image.new("RGB", (SIZE, SIZE))
    out.paste(left, (0, 0))
    out.paste(right, (512, 0))
    return np.asarray(out, np.float32) / 255


def board(text, aspect, fonts, bg, fg, display=False):
    h = 200
    w = int(aspect * h)
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, w - 5, h - 5], outline=tuple(min(255, c + 60) for c in bg), width=6)
    size = 150
    while size > 20:
        f = _font(fonts, "DisplayFont" if display else "UIFont", size)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] < w * 0.92 and bb[3] - bb[1] < h * 0.78:
            break
        size -= 6
    bb = d.textbbox((0, 0), text, font=f)
    x = (w - (bb[2] - bb[0])) / 2 - bb[0]
    y = (h - (bb[3] - bb[1])) / 2 - bb[1]
    d.text((x + 4, y + 4), text, font=f, fill=tuple(int(c * 0.35) for c in bg))
    d.text((x, y), text, font=f, fill=fg)
    return im.resize((SIZE, SIZE // 16), Image.LANCZOS)


def signs_layer(fonts, which):
    out = Image.new("RGB", (SIZE, SIZE))
    if which == 1:
        for i, t in enumerate(SHOP_SIGNS):
            bg, fg = BOARD[i % len(BOARD)]
            if t == "HOSPITAL":
                bg, fg = (240, 240, 245), (200, 20, 20)
            if t == "POLICE STATION":
                bg, fg = (20, 50, 140), (255, 255, 255)
            if t == "DANGA ARMS":
                bg, fg = (25, 25, 25), (255, 120, 20)
            if t == "FASHION POINT":
                bg, fg = (255, 80, 140), (255, 255, 255)
            out.paste(board(t, SIGN_ASPECT.get(t, 5.5), fonts, bg, fg, display=t in ("DANGA ARMS",)), (0, i * SIZE // 16))
    else:
        for i, (t, a) in enumerate(SIGNS2):
            bg, fg = ((245, 240, 225), (120, 20, 20)) if i not in (1, 3, 8) else ((20, 40, 90), (255, 255, 255))
            if t == "INDIA":
                bg, fg = (250, 250, 250), (20, 60, 140)
            out.paste(board(t, a, fonts, bg, fg, display=t in ("INDIA", "AGARTALA")), (0, i * SIZE // 16))
    return np.asarray(out, np.float32) / 255


def paint_layer():
    n = noise((SIZE, SIZE), 16, 3) * 0.6 + noise((SIZE, SIZE), 4, 4) * 0.4
    wear = np.clip((noise((SIZE, SIZE), 12, 5) - 0.78) * 2.0, 0, 1) * 0.18
    v = np.clip(0.93 + 0.06 * (n - 0.5) - wear, 0, 1)
    return np.stack([v, v, v * 0.98], -1)


def paddy_layer(tex):
    g = np.asarray(_load(os.path.join(tex, "grass", "diff.jpg")), np.float32) / 255
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    rows = 0.85 + 0.15 * np.sin(xx / 6.0)
    img = g * np.array([1.05, 1.08, 0.7]) * rows[..., None]
    water = (noise((SIZE, SIZE), 128, 9) > 0.7)[..., None]
    img = np.where(water, img * 0.6 + np.array([0.1, 0.13, 0.12]), img)
    return np.clip(img, 0, 1)


def cutout(leaves_dir, name):
    d = os.path.join(leaves_dir, name)
    if not os.path.isdir(d):
        return None
    files = os.listdir(d)
    diff = [f for f in files if f.startswith("diff")]
    if not diff:
        return None
    rgba = Image.open(os.path.join(d, diff[0]))
    rgb = rgba.convert("RGB")
    if "A" in rgba.getbands():
        a = rgba.getchannel("A")
    else:
        a = None
    al = [f for f in files if f.startswith("alpha")]
    if al:
        a = _load(os.path.join(d, al[0]), "L")
        a = a.resize(rgb.size)
    if a is None:
        a = Image.new("L", rgb.size, 255)
    return np.dstack([np.asarray(rgb, np.float32) / 255, np.asarray(a, np.float32) / 255])


def _components(alpha, thr=0.5, min_px=400):
    from scipy import ndimage
    lab, n = ndimage.label(alpha > thr)
    objs = ndimage.find_objects(lab)
    out = []
    for i, sl in enumerate(objs):
        m = lab[sl] == (i + 1)
        if m.sum() >= min_px:
            out.append((m.sum(), sl, m))
    out.sort(key=lambda t: -t[0])
    return out


def leaf_cluster(leaves_dir, seed=1):
    src = cutout(leaves_dir, "island_tree_01_leaves")
    if src is None:
        src = cutout(leaves_dir, "jacaranda_tree_leaves")
    out = np.zeros((SIZE, SIZE, 4), np.float32)
    if src is None:
        return out
    comps = _components(src[..., 3])
    pieces = []
    for _, sl, m in comps[:8]:
        piece = src[sl].copy()
        piece[..., 3] *= m
        pieces.append(Image.fromarray((piece * 255).astype(np.uint8), "RGBA"))
    rnd = random.Random(seed)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for k in range(260):
        p = pieces[rnd.randrange(len(pieces))]
        s = rnd.uniform(0.12, 0.22) * SIZE / max(p.size)
        q = p.resize((max(4, int(p.size[0] * s)), max(4, int(p.size[1] * s))), Image.LANCZOS).rotate(rnd.uniform(0, 360), expand=True)
        # keep the cluster round: denser in the middle
        r = (rnd.random() ** 0.7) * SIZE * 0.42
        a = rnd.uniform(0, 2 * math.pi)
        x = int(SIZE / 2 + r * math.cos(a) - q.size[0] / 2)
        y = int(SIZE / 2 + r * math.sin(a) - q.size[1] / 2)
        shade = rnd.uniform(0.7, 1.05)
        qa = np.asarray(q, np.float32)
        qa[..., :3] *= shade
        canvas.alpha_composite(Image.fromarray(np.clip(qa, 0, 255).astype(np.uint8), "RGBA"), (x, y))
    return np.asarray(canvas, np.float32) / 255


def palm_frond(leaves_dir):
    src = cutout(leaves_dir, "jacaranda_tree_leaves")
    out = np.zeros((SIZE, SIZE, 4), np.float32)
    if src is None:
        return out
    comps = _components(src[..., 3])
    if not comps:
        return out
    _, sl, m = comps[0]
    piece = src[sl].copy()
    piece[..., 3] *= m
    ys, xs = np.nonzero(m)
    cov = np.cov(np.stack([xs - xs.mean(), ys - ys.mean()]))
    w, v = np.linalg.eigh(cov)
    ax = v[:, np.argmax(w)]
    ang = math.degrees(math.atan2(ax[1], ax[0]))
    im = Image.fromarray((piece * 255).astype(np.uint8), "RGBA").rotate(ang - 90, expand=True, resample=Image.BICUBIC)
    bb = im.getbbox()
    im = im.crop(bb)
    im = im.resize((SIZE, SIZE), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


def banana_leaf(leaves_dir):
    src = cutout(leaves_dir, "island_tree_01_leaves")
    out = np.zeros((SIZE, SIZE, 4), np.float32)
    if src is None:
        return out
    comps = _components(src[..., 3])
    if not comps:
        return out
    _, sl, m = comps[0]
    piece = src[sl].copy()
    piece[..., 3] *= m
    ys, xs = np.nonzero(m)
    cov = np.cov(np.stack([xs - xs.mean(), ys - ys.mean()]))
    w, v = np.linalg.eigh(cov)
    ax = v[:, np.argmax(w)]
    ang = math.degrees(math.atan2(ax[1], ax[0]))
    im = Image.fromarray((piece * 255).astype(np.uint8), "RGBA").rotate(ang - 90, expand=True, resample=Image.BICUBIC)
    im = im.crop(im.getbbox()).resize((SIZE, SIZE), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    a[..., :3] = np.clip(a[..., :3] * np.array([1.05, 1.15, 0.8]) + np.array([0.02, 0.05, 0.0]), 0, 1)
    return a


def fern_layer(leaves_dir):
    src = cutout(leaves_dir, "fern_02_main")
    if src is None:
        return np.zeros((SIZE, SIZE, 4), np.float32)
    return np.asarray(Image.fromarray((src * 255).astype(np.uint8), "RGBA").resize((SIZE, SIZE), Image.LANCZOS), np.float32) / 255


def glass_layer():
    yy, xx = np.mgrid[0:SIZE, 0:SIZE] / SIZE
    img = np.stack([0.15 + 0.3 * (1 - yy), 0.2 + 0.33 * (1 - yy), 0.28 + 0.35 * (1 - yy)], -1)
    img += (np.abs(((xx + yy * 0.5) * 7) % 1.0 - 0.5) < 0.06)[..., None] * 0.1
    return np.clip(img, 0, 1)


def build_layers(tex, leaves, fonts, out_dir):
    """Writes out_dir/<index>_<name>.png (RGBA) and <index>_<name>_n.png (normal map) for every layer."""
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for i, name in enumerate(LAYERS):
        nrm = None
        rgba = None
        if name in PHOTO:
            p = os.path.join(tex, name, "diff.jpg")
            if os.path.exists(p):
                rgb = np.asarray(_load(p), np.float32) / 255
                np_ = os.path.join(tex, name, "nor.jpg")
                if os.path.exists(np_):
                    nrm = np.asarray(_load(np_), np.float32) / 255
            else:
                rgb = np.full((SIZE, SIZE, 3), 0.6, np.float32) * (0.9 + 0.1 * noise((SIZE, SIZE), 32, i))[..., None]
                report.append("missing photo for %s - grey stand-in" % name)
            rgba = np.dstack([rgb, np.ones((SIZE, SIZE), np.float32)])
        elif name == "window":
            rgba = np.dstack([window_layer(tex), np.ones((SIZE, SIZE))])
        elif name == "shopfront":
            rgba = np.dstack([shopfront_layer(tex), np.ones((SIZE, SIZE))])
        elif name == "signs":
            rgba = np.dstack([signs_layer(fonts, 1), np.ones((SIZE, SIZE))])
        elif name == "signs2":
            rgba = np.dstack([signs_layer(fonts, 2), np.ones((SIZE, SIZE))])
        elif name == "markings":
            rgba = np.dstack([paint_layer(), np.ones((SIZE, SIZE))])
        elif name == "paddy":
            rgba = np.dstack([paddy_layer(tex), np.ones((SIZE, SIZE))])
        elif name == "leaves":
            rgba = leaf_cluster(leaves)
        elif name == "palmleaf":
            rgba = palm_frond(leaves)
        elif name == "bananaleaf":
            rgba = banana_leaf(leaves)
        elif name == "fern":
            rgba = fern_layer(leaves)
        elif name == "white":
            v = 0.94 + 0.04 * noise((SIZE, SIZE), 32, 11)
            rgba = np.dstack([v, v, v, np.ones((SIZE, SIZE))])
        elif name == "glass":
            rgba = np.dstack([glass_layer(), np.ones((SIZE, SIZE))])
        if rgba is None:
            rgba = np.ones((SIZE, SIZE, 4), np.float32) * 0.5
        # foliage: bleed colour into the transparent parts so mip-maps do not get dark halos
        if name in ("leaves", "palmleaf", "bananaleaf", "fern"):
            a = rgba[..., 3:4]
            col = rgba[..., :3]
            blur = np.asarray(Image.fromarray((col * a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12)), np.float32) / 255
            wsum = np.asarray(Image.fromarray((a[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12)), np.float32)[..., None] / 255
            fill = blur / np.maximum(wsum, 1e-3)
            rgba[..., :3] = np.where(a > 0.5, col, np.clip(fill, 0, 1))
        Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(out_dir, "%02d_%s.png" % (i, name)))
        if nrm is None:
            nrm = np.ones((8, 8, 3), np.float32) * np.array([0.5, 0.5, 1.0])
            Image.fromarray((nrm * 255).astype(np.uint8)).resize((SIZE, SIZE)).save(os.path.join(out_dir, "%02d_%s_n.png" % (i, name)))
        else:
            Image.fromarray((np.clip(nrm, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out_dir, "%02d_%s_n.png" % (i, name)))
    return report


# ------------------------------------------------------------------------------------------------ minimap picture
def map_picture(roads, grid, buildings, path, size=2048):
    H = LY.HALF
    xs = np.linspace(-H, H, size // 2)
    X, Z = np.meshgrid(xs, -xs)
    h = LY.height(X, Z)
    wet = ~np.isnan(LY.water_info(X, Z))
    img = np.zeros(X.shape + (3,), np.float32)
    img[:] = np.array([0.20, 0.27, 0.20])
    shade = np.clip(np.gradient(h, axis=1) * 0.6 + np.gradient(h, axis=0) * -0.6, -0.15, 0.15)
    img += shade[..., None]
    img += np.clip(h, 0, 25)[..., None] / 25.0 * np.array([0.12, 0.1, 0.05])
    img[wet] = np.array([0.20, 0.42, 0.62])
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
    d = ImageDraw.Draw(im)

    def P(x, z):
        return ((x + H) / (2 * H) * size, (H - z) / (2 * H) * size)
    occ = grid.occ
    gs = grid.cell
    # parks / sites in green-grey, buildings in light grey
    site = (occ == 3)
    bld = (occ == 2)
    over = np.zeros(occ.shape + (4,), np.uint8)
    over[site] = (90, 120, 85, 255)
    over[bld] = (150, 148, 140, 255)
    ov = Image.fromarray(over[::-1], "RGBA").resize((size, size), Image.NEAREST)
    im = Image.alpha_composite(im.convert("RGBA"), ov)
    d = ImageDraw.Draw(im)
    for c in roads.chains:
        pts = c["pts"]
        wpx = max(2, int(LY.ROAD_W[c["cls"]] / (2 * H) * size * 1.6))
        d.line([P(*p) for p in pts], fill=(70, 70, 72, 255), width=wpx + 4, joint="curve")
    for c in roads.chains:
        pts = c["pts"]
        wpx = max(2, int(LY.ROAD_W[c["cls"]] / (2 * H) * size * 1.6))
        colr = (235, 235, 230, 255) if c["cls"] == "A" else (215, 215, 210, 255) if c["cls"] == "B" else (190, 188, 180, 255)
        d.line([P(*p) for p in pts], fill=colr, width=wpx, joint="curve")
    for n in range(len(roads.g.nodes)):
        if roads.g.degree(n) >= 3:
            x, z = roads.g.nodes[n]
            r = LY.ROAD_W["A"] / (2 * H) * size * 0.9
            q = P(x, z)
            d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=(225, 225, 220, 255))
    # runway
    a, b = P(-700, 1013), P(700, 967)
    d.rectangle([a[0], a[1], b[0], b[1]], fill=(110, 110, 112, 255))
    if LY.RAIL_X:
        x0, z0 = LY.RAIL_X[0], LY.RAIL_Z
        d.line([P(x0, z0), P(LY.RAIL_X[1], z0)], fill=(120, 100, 90, 255), width=4)
    im.convert("RGB").save(path)


# ------------------------------------------------------------------------------------------------ ground light map
def light_map(colliders, shade, path, size=2048, sun_az=150.0, sun_el=52.0):
    """Soft contact shadows (AO) and the sun shadows of every building, wall and tree, as one grey picture that the
    ground and road shaders multiply by (world x, z -> u, v)."""
    H = LY.HALF
    cell = 2 * H / size
    hmap = np.zeros((size, size), np.float32)          # [row = z from south][col = x]
    for cx, cy, cz, sx, sy, sz, yaw in colliders:
        ground = float(LY.height(np.array([cx]), np.array([cz]))[0])
        top = cy + sy - max(ground, LY.SEA_LEVEL)          # height above the ground it stands on
        if sy < 0.6 or top < 0.5:
            continue
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        hx, hz = sx / 2, sz / 2
        corners = [(cx + x * c + z * s, cz - x * s + z * c) for x, z in ((-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz))]
        xs = [p[0] for p in corners]
        zs = [p[1] for p in corners]
        i0, i1 = int((min(xs) + H) / cell), int((max(xs) + H) / cell) + 1
        j0, j1 = int((min(zs) + H) / cell), int((max(zs) + H) / cell) + 1
        i0, j0 = max(0, i0), max(0, j0)
        i1, j1 = min(size, i1), min(size, j1)
        if i1 <= i0 or j1 <= j0:
            continue
        gx = (np.arange(i0, i1) + 0.5) * cell - H
        gz = (np.arange(j0, j1) + 0.5) * cell - H
        GX, GZ = np.meshgrid(gx, gz)
        lx = (GX - cx) * c - (GZ - cz) * s
        lz = (GX - cx) * s + (GZ - cz) * c
        inside = (np.abs(lx) <= hx + cell * 0.5) & (np.abs(lz) <= hz + cell * 0.5)
        sub = hmap[j0:j1, i0:i1]
        sub[inside] = np.maximum(sub[inside], top)
    # sun shadows: march against the sun direction
    az = math.radians(sun_az)
    dx, dz = -math.sin(az), -math.cos(az)              # shadows fall away from the sun
    tan_el = math.tan(math.radians(sun_el))
    shadow = np.zeros_like(hmap)
    for k in range(1, 40):
        dist = k * cell
        sx, sz = int(round(dx * k)), int(round(dz * k))
        shifted = np.roll(np.roll(hmap, sz, axis=0), sx, axis=1) - dist * tan_el
        shadow = np.maximum(shadow, (shifted > 0.2).astype(np.float32))
    # trees: soft round shade
    tree = np.zeros_like(hmap)
    for x, z, r, s in shade:
        ox, oz = x + dx * 3.0, z + dz * 3.0
        i, j = int((ox + H) / cell), int((oz + H) / cell)
        rr = max(1, int(r / cell))
        i0, i1, j0, j1 = max(0, i - rr), min(size, i + rr + 1), max(0, j - rr), min(size, j + rr + 1)
        if i1 <= i0 or j1 <= j0:
            continue
        gy, gx = np.mgrid[j0:j1, i0:i1]
        d = np.hypot(gx - i, gy - j) / rr
        tree[j0:j1, i0:i1] = np.maximum(tree[j0:j1, i0:i1], np.clip(1 - d, 0, 1) * s * 1.6)
    occ = (hmap > 0.3).astype(np.float32)
    ao = np.asarray(Image.fromarray((occ * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
    sh = np.asarray(Image.fromarray((shadow * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    tr = np.asarray(Image.fromarray((np.clip(tree, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.0)), np.float32) / 255
    light = (1 - 0.55 * sh) * (1 - 0.45 * ao) * (1 - 0.45 * tr)
    light = np.clip(light, 0.25, 1.0)
    # row 0 of the picture = north (Unity reads the bottom row as v = 0 = south)
    Image.fromarray((light[::-1] * 255).astype(np.uint8), "L").save(path)
    return light
