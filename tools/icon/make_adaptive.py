"""Android launcher versions of the Moulika icon (same artwork as the Play Store icon):
- legacy: the square Play Store icon as it is
- adaptive background: the artwork without the badge, filling the whole 108 dp layer (launchers show the middle 72 dp)
- adaptive foreground: the MX badge alone, inside the 66 dp safe circle so no launcher mask cuts it
- round: the visible middle of the artwork plus the badge, cut to a circle
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

sys.path.insert(0, "/home/claude/icon")
import make_icon as M

S = 1024


def art():
    rng = np.random.default_rng(7)
    bg = Image.fromarray(np.clip(M.background(rng), 0, 255).astype(np.uint8)).convert("RGBA")
    face = Image.open(M.FACE).convert("RGBA")
    rgb, alpha = face.convert("RGB"), face.getchannel("A")
    rgb = ImageEnhance.Contrast(rgb).enhance(1.18)
    rgb = ImageEnhance.Brightness(rgb).enhance(0.94)
    fa = np.asarray(rgb, np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    shade = 1 - 0.5 * np.clip((xx / S - 0.55) * 1.6 + (yy / S - 0.6) * 1.6, 0, 1)
    fa *= shade[..., None]
    face = Image.fromarray(np.clip(fa, 0, 255).astype(np.uint8)).convert("RGBA")
    face.putalpha(alpha)
    face = M.eye_glow(face)
    bg.alpha_composite(face)
    return M.grade(bg).convert("RGBA")


def badge(img, cx, cy, bw, bh, cell, border, radius, shadow):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0 = int(cx - bw / 2), int(cy - bh / 2)
    x1, y1 = x0 + bw, y0 + bh
    d.rounded_rectangle((x0 + shadow[0], y0 + shadow[1], x1 + shadow[0], y1 + shadow[1]), radius, fill=(0, 0, 0, 120))
    d.rounded_rectangle((x0, y0, x1, y1), radius, fill=(8, 8, 10, 245), outline=(214, 32, 26, 255), width=border)
    word = "MX"
    tw = (len(word) * 5 + (len(word) - 1)) * cell
    th = 5 * cell
    ox, oy = x0 + (bw - tw) // 2, y0 + (bh - th) // 2
    off = max(2, cell // 4)
    for dx, dy, col in [(off, off, (150, 12, 10, 255)), (0, 0, (250, 248, 240, 255))]:
        for li, ch in enumerate(word):
            for r, row in enumerate(M.PIX[ch]):
                for c, bit in enumerate(row):
                    if bit == "1":
                        px = ox + (li * 6 + c) * cell + dx
                        py = oy + r * cell + dy
                        d.rectangle((px, py, px + cell - 1, py + cell - 1), fill=col)


def main(out):
    base = art()                                   # the artwork without the badge, 1024 px
    lo, hi = S * 18 / 108, S * 90 / 108            # the part of a 108 dp layer launchers show (72 dp)
    vis = hi - lo                                  # 683 px
    # background: the whole artwork over the visible part (a hair larger so no edge shows), the layer's outer
    # margin filled with a soft blurred copy (only seen during launcher animations)
    from PIL import ImageFilter
    layer = base.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30)).convert("RGBA")
    sharp_px = int(vis + 20)
    sharp = base.resize((sharp_px, sharp_px), Image.LANCZOS)
    feather = Image.new("L", (sharp_px, sharp_px), 0)
    ImageDraw.Draw(feather).rectangle((6, 6, sharp_px - 7, sharp_px - 7), fill=255)
    feather = feather.filter(ImageFilter.GaussianBlur(3))
    o = (S - sharp_px) // 2
    layer.paste(sharp, (o, o), feather)
    layer.convert("RGB").save(out + "/moulika_icon_bg.png")
    # foreground: the MX badge, bottom left as on the Play Store icon but pulled inside the 66 dp safe circle
    fg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bcx, bcy, bw, bh = 372, 660, 171, 122
    badge(fg, bcx, bcy, bw, bh, 11, 5, 12, (3, 5))
    far = np.hypot(512 - (bcx - bw / 2), (bcy + bh / 2) - 512)
    print("badge far corner from centre: %.0f px (safe circle 313)" % far)
    fg.save(out + "/moulika_icon_fg.png")
    # round (Android 7.1 launchers): the visible part with the badge, cut to a circle
    k = S / vis
    rv = layer.crop((int(lo), int(lo), int(hi), int(hi))).resize((S, S), Image.LANCZOS)
    badge(rv, (bcx - lo) * k, (bcy - lo) * k, int(bw * k), int(bh * k), 16, 8, 18, (5, 7))
    mask = Image.new("L", (S * 2, S * 2), 0)
    ImageDraw.Draw(mask).ellipse((4, 4, S * 2 - 4, S * 2 - 4), fill=255)
    mask = mask.resize((S, S), Image.LANCZOS)
    rnd = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rnd.paste(rv, (0, 0), mask)
    rnd.save(out + "/moulika_icon_round.png")
    # previews: Play Store icon, adaptive icon under a squircle (Samsung) and a circle mask, round icon
    full = layer.copy()
    full.alpha_composite(fg)
    v = full.crop((int(lo), int(lo), int(hi), int(hi))).resize((240, 240), Image.LANCZOS)
    play = Image.open("/home/claude/icon/out/moulika_icon_1024.png").convert("RGBA").resize((240, 240), Image.LANCZOS)
    prev = Image.new("RGBA", (1000, 256), (40, 40, 40, 255))
    sq = Image.new("L", (240, 240), 0)
    ImageDraw.Draw(sq).rounded_rectangle((0, 0, 239, 239), 72, fill=255)
    prev.paste(play, (8, 8), sq)
    prev.paste(v, (256, 8), sq)
    ci = Image.new("L", (240, 240), 0)
    ImageDraw.Draw(ci).ellipse((0, 0, 239, 239), fill=255)
    prev.paste(v, (504, 8), ci)
    prev.alpha_composite(rnd.resize((240, 240), Image.LANCZOS), (752, 8))
    prev.save(out + "/preview_adaptive.png")
    print("written")


if __name__ == "__main__":
    main(sys.argv[1])
