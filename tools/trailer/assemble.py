"""Cuts, grades and scores the two Moulika trailers from the rendered frames.

    python3 tools/trailer/assemble.py BUILD_DIR

BUILD_DIR/frames/f_NNNN.png (Blender), BUILD_DIR/trailer/trailer_shots.json, BUILD_DIR/trailer_audio/sounds/*.ogg (trailer
effects), BUILD_DIR/game_sounds/sounds/*.ogg (the game's recordings). Writes BUILD_DIR/out/moulika_trailer.mp4,
moulika_short_trailer.mp4 and a few stills. The only words on screen are on the end card: the game's name, the
subtitle, and itch.io.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

B = os.path.abspath(sys.argv[1])
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT = os.path.join(ROOT, "game", "fonts", "dk_midnight_chalker.otf")
FPS = 24
SR = 48000
W, H = 1920, 1080
OUT = os.path.join(B, "out")
os.makedirs(OUT, exist_ok=True)
SHOTS = json.load(open(os.path.join(B, "trailer", "trailer_shots.json")))


def log(*a):
    print("[assemble]", *a, flush=True)


def shot(name):
    return next(s for s in SHOTS if s["name"] == name)


# ---------------------------------------------------------------------------------------------- the end card
def font(size):
    return ImageFont.truetype(FONT, size)


def spaced(draw_img, text, fnt, y, color, tracking, alpha):
    """Text centred at y with extra letter spacing, drawn onto an RGBA layer."""
    d = ImageDraw.Draw(draw_img)
    widths = [fnt.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=fnt, fill=color[:3] + (int(255 * alpha),))
        x += w + tracking


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def end_card_frames(plate_path, seconds, dest, start_index):
    plate = Image.open(plate_path).convert("RGB").resize((W, H), Image.LANCZOS)
    plate = plate.filter(ImageFilter.GaussianBlur(16))
    plate = ImageEnhance.Color(plate).enhance(0.85)
    plate = ImageEnhance.Brightness(plate).enhance(0.72)
    a = np.asarray(plate, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.35 * np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2 - 0.3, 0, None)
    plate = Image.fromarray(np.clip(a * v[..., None], 0, 255).astype(np.uint8))
    f_title, f_sub, f_itch = font(250), font(66), font(46)
    tw = f_title.getlength("MOULIKA")
    n = round(seconds * FPS)
    for i in range(n):
        t = i / FPS
        bg = ease(t / 1.0)
        a_title = ease((t - 0.8) / 1.4)
        a_sub = ease((t - 2.0) / 1.0)
        a_itch = ease((t - 3.0) / 1.0)
        out_fade = 1.0 - ease((t - (seconds - 0.8)) / 0.8)
        frame = Image.new("RGB", (W, H), (0, 0, 0))
        frame = Image.blend(frame, plate, bg)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if a_title > 0:
            s = 1.0 + 0.07 * (1 - a_title)
            size = int(250 * s)
            ft = font(size)
            w_t = ft.getlength("MOULIKA")
            ty = 330 - (size - 250) * 0.5
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).text(((W - w_t) / 2, ty), "MOULIKA", font=ft, fill=(200, 20, 10, int(200 * a_title)))
            glow = glow.filter(ImageFilter.GaussianBlur(28))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).text(((W - w_t) / 2 + 6, ty + 8), "MOULIKA", font=ft, fill=(0, 0, 0, int(220 * a_title)))
            shadow = shadow.filter(ImageFilter.GaussianBlur(6))
            layer = Image.alpha_composite(layer, glow)
            layer = Image.alpha_composite(layer, shadow)
            ImageDraw.Draw(layer).text(((W - w_t) / 2, ty), "MOULIKA", font=ft, fill=(184, 16, 10, int(255 * a_title)))
        if a_sub > 0:
            spaced(layer, "THE INDIAN HORROR GAME", f_sub, 640, (236, 232, 222), 8, a_sub)
        if a_itch > 0:
            spaced(layer, "ALSO AVAILABLE ON ITCH.IO", f_itch, 880, (205, 205, 200), 5, a_itch * 0.95)
        frame = Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")
        if out_fade < 1.0:
            frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, out_fade)
        frame.save(os.path.join(dest, "%05d.png" % (start_index + i)))
    return n


# ---------------------------------------------------------------------------------------------- the picture
def build_sequence(name, shot_names, dips, black_s, card_s, plate):
    """Graded part (Blender frames) and card part (black + end card) as two numbered image folders."""
    gdir = os.path.join(B, "seq_%s_grade" % name)
    cdir = os.path.join(B, "seq_%s_card" % name)
    for d in (gdir, cdir):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    k = 0
    missing = 0
    for sn in shot_names:
        s = shot(sn)
        n = s["f1"] - s["f0"] + 1
        for j in range(n):
            src = os.path.join(B, "frames", "f_%04d.png" % (s["f0"] + j))
            dst = os.path.join(gdir, "%05d.png" % k)
            if not os.path.exists(src):
                missing += 1
                Image.new("RGB", (W, H), (0, 0, 0)).save(dst)
            else:
                # a short dip to black at the slow cuts
                fade = 1.0
                if sn in dips:
                    fade = min(fade, min(1.0, (j + 1) / 5.0), min(1.0, (n - j) / 5.0))
                if fade < 1.0:
                    im = Image.open(src).convert("RGB")
                    Image.blend(Image.new("RGB", im.size, (0, 0, 0)), im, fade).save(dst)
                else:
                    os.symlink(src, dst)
            k += 1
    nb = round(black_s * FPS)
    for j in range(nb):
        Image.new("RGB", (W, H), (0, 0, 0)).save(os.path.join(cdir, "%05d.png" % j))
    nc = end_card_frames(plate, card_s, cdir, nb)
    log("%s: %d graded frames (%d missing), %d card frames" % (name, k, missing, nb + nc))
    return gdir, cdir, k, nb + nc


# ---------------------------------------------------------------------------------------------- the sound
_cache = {}


def load(name):
    if name in _cache:
        return _cache[name]
    for d in (os.path.join(B, "trailer_audio", "sounds"), os.path.join(B, "game_sounds", "sounds")):
        p = os.path.join(d, name + ".ogg")
        if os.path.exists(p):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                                 capture_output=True, check=True).stdout
            x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
            _cache[name] = x
            return x
    log("  (no sound %s)" % name)
    _cache[name] = None
    return None


def mix(events, seconds):
    out = np.zeros((int(seconds * SR) + SR, 2), np.float32)
    for ev in events:
        t, name, gain = ev[0], ev[1], ev[2]
        o = ev[3] if len(ev) > 3 else {}
        x = load(name)
        if x is None or t >= seconds:
            continue
        if o.get("rate", 1.0) != 1.0:
            r = o["rate"]
            idx = np.arange(0, len(x) - 1, r)
            i0 = idx.astype(int)
            fr = (idx - i0)[:, None]
            x = x[i0] * (1 - fr) + x[np.minimum(i0 + 1, len(x) - 1)] * fr
        if o.get("offset"):
            x = x[int(o["offset"] * SR):]
        dur = o.get("dur")
        if dur:
            n = int(dur * SR)
            if o.get("loop") and len(x) < n:
                x = np.tile(x, (n // max(len(x), 1) + 1, 1))
            x = x[:n]
        x = x.copy()
        fi, fo = int(o.get("fade_in", 0.0) * SR), int(o.get("fade_out", 0.02) * SR)
        if fi > 0:
            x[:fi] *= np.linspace(0, 1, min(fi, len(x)))[:, None][: len(x[:fi])]
        if fo > 0 and len(x) > fo:
            x[-fo:] *= np.linspace(1, 0, fo)[:, None]
        boost = 0.0 if o.get("hit") else BED_BOOST
        g = 10 ** ((gain + boost) / 20.0)
        if "gain_to" in o:
            g2 = 10 ** ((o["gain_to"] + boost) / 20.0)
            x *= np.linspace(g, g2, len(x))[:, None]
        else:
            x *= g
        if o.get("pan"):
            p = o["pan"]
            x[:, 0] *= min(1.0, 1 - p)
            x[:, 1] *= min(1.0, 1 + p)
        s = int(t * SR)
        e = min(len(out), s + len(x))
        out[s:e] += x[: e - s]
    out = out[: int(seconds * SR)]
    # level set by the loud moments rather than the single loudest peak, then a soft limiter (peaks about -1 dB):
    # the scare still hits hardest, but the quiet build-up stays audible on a phone speaker
    ref = float(np.percentile(np.abs(out), 99.9)) + 1e-9
    out = np.tanh(out / ref * 0.9) * 0.89
    return out


BED_BOOST = 7.0      # everything but the scare hits, so the build-up carries on a phone speaker


def write_wav(x, path):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", path],
                   input=pcm.tobytes(), check=True)


def steps(t0, t1, every, name_base, gain, start_gain=None, payal=None, n_var=6):
    """Footsteps (and her payal) from t0 to t1."""
    ev = []
    t, i = t0, 0
    count = max(int((t1 - t0) / every), 1)
    while t < t1:
        g = gain if start_gain is None else start_gain + (gain - start_gain) * (i / count)
        ev.append((t, "%s_%d" % (name_base, i % n_var + 1), g))
        if payal is not None:
            ev.append((t + 0.02, "payal", g + payal, {"dur": 0.6, "fade_out": 0.25, "offset": 0.05 * (i % 4)}))
        t += every
        i += 1
    return ev


def at(name, dt=0.0, base=None):
    """seconds from the trailer's start for a moment dt seconds into shot `name`"""
    return (shot(name)["f0"] - base) / FPS + dt


def score_full(total):
    b = shot("ext")["f0"]
    T = lambda n, dt=0.0: at(n, dt, b)  # noqa: E731
    lunge = T("lunge")
    ev = [
        (0.0, "t_wind", -16, {"dur": 13.0, "loop": True, "fade_in": 1.5, "fade_out": 3.0}),
        (0.0, "night", -22, {"dur": 9.5, "loop": True, "fade_in": 1.0, "fade_out": 2.5}),
        (1.2, "dog_howl", -15, {"pan": -0.4}),
        (3.4, "owl", -21, {"pan": 0.5}),
        (2.0, "game_music", -12, {"dur": lunge - 2.0 + 0.1, "loop": True, "fade_in": 4.0, "fade_out": 0.3}),
        (T("class"), "t_drone", -20, {"dur": lunge - T("class") + 0.1, "loop": True, "fade_in": 2.0, "fade_out": 0.3, "gain_to": -10}),
        (T("veranda", 1.5), "payal", -26, {"pan": 0.6}),
        (T("veranda", 2.4), "payal", -24, {"pan": 0.5}),
        (T("class"), "t_boom", -15),
        (T("class"), "t_flicker", -17, {"dur": 4.0, "loop": True, "fade_out": 0.3}),
        (T("class", 1.0), "heartbeat", -15, {"dur": 10.0, "loop": True, "fade_in": 1.0, "fade_out": 0.5}),
    ]
    ev += steps(T("feet", 0.1), T("feet", 3.0), 0.69, "footstep", -13, payal=1)
    ev += steps(T("corridor", 0.2), T("corridor", 4.5), 0.517, "footstep", -11, start_gain=-24, payal=0)
    ev += [
        (T("corridor"), "heartbeat", -13, {"dur": 7.5, "loop": True, "rate": 1.25, "fade_out": 0.5}),
        (T("hide"), "t_breath", -12, {"dur": 3.0, "fade_in": 0.3, "fade_out": 0.4}),
    ]
    ev += steps(T("hide", 0.1), T("hide", 3.0), 0.74, "footstep", -16, payal=2)
    ev += [
        (T("door"), "t_boom", -9), (T("door", 0.25), "door_locked", -10),
        (T("padlock"), "t_boom", -10), (T("padlock", 0.2), "unlock", -15),
        (T("key"), "t_boom", -10), (T("key", 0.25), "pickup", -12),
        (T("hammer"), "t_boom", -9), (T("hammer", 0.3), "hammer_hit", -14),
        (T("hall", 0.2), "t_riser", -18, {"dur": 3.9, "gain_to": -6, "fade_out": 0.1}),
        (T("chase_a") - 0.04, "t_braam", -7),
        (T("hall", 0.0), "heartbeat", -12, {"dur": 9.0, "loop": True, "rate": 1.55, "fade_out": 0.3}),
        (T("chase_a"), "t_reverse", -10, {"offset": 0.0}),
        (T("chase_a"), "t_breath", -9, {"dur": 5.0, "rate": 1.15, "fade_out": 0.2}),
    ]
    ev += steps(T("chase_a", 0.05), T("chase_b", 2.5), 0.32, "footstep", -9, payal=2)
    ev += [
        (T("chase_b"), "t_whoosh", -9),
        (T("chase_b", 2.15), "t_whoosh", -4),
        # the lunge: a breath of silence, then everything at once
        (lunge + 0.28, "t_stinger", -3, {"hit": True}),
        (lunge + 0.3, "scream", -2, {"hit": True}),
        (lunge + 0.42, "t_boom", -1, {"hit": True}),
        (lunge + 0.55, "whack", -5, {"hit": True}),
    ]
    card = T("lunge") + 1.5 + 1.0
    ev += [
        (card + 0.75, "t_braam", -6),
        (card + 0.75, "t_boom", -10),
        (card + 2.1, "payal", -17),
        (card, "t_drone", -20, {"dur": total - card, "loop": True, "fade_in": 1.0, "fade_out": 1.5}),
        (card, "t_wind", -26, {"dur": total - card, "loop": True, "fade_in": 1.0, "fade_out": 1.5}),
    ]
    return ev


def score_short(total):
    b = shot("s_walk")["f0"]
    T = lambda n, dt=0.0: at(n, dt, b)  # noqa: E731
    scare = T("s_scare", 1.32)
    ev = [
        (0.0, "game_music", -14, {"dur": scare - 0.55, "loop": True, "fade_in": 1.0, "fade_out": 0.9}),
        (0.0, "t_wind", -24, {"dur": scare - 0.5, "loop": True, "fade_in": 1.0, "fade_out": 0.8}),
        (0.8, "heartbeat", -16, {"dur": scare - 1.3, "loop": True, "rate": 1.2, "fade_in": 1.0, "fade_out": 0.6, "gain_to": -9}),
        (T("s_walk", 3.0), "payal", -25, {"pan": 0.2}),
        (T("s_walk", 3.55), "payal", -23, {"pan": -0.1}),
        (T("s_walk", 4.1), "payal", -22, {"pan": -0.35}),
        (T("s_class", 0.15), "door_open", -12),
    ]
    ev += steps(0.3, T("s_class", 3.3), 0.62, "footstep", -21)
    ev += [
        (scare - 0.35, "t_whoosh", -10),
        (scare, "t_stinger", -1, {"hit": True}),
        (scare + 0.02, "scream", 0, {"hit": True}),
        (scare + 0.1, "t_boom", 0, {"hit": True}),
        (scare + 0.35, "whack", -3, {"hit": True}),
    ]
    card = T("s_scare") + 2.7 + 0.8
    ev += [
        (card + 0.75, "t_braam", -6),
        (card + 0.75, "t_boom", -10),
        (card + 2.1, "payal", -17),
        (card, "t_drone", -20, {"dur": total - card, "loop": True, "fade_in": 1.0, "fade_out": 1.5}),
    ]
    return ev


# ---------------------------------------------------------------------------------------------- encode
GRADE = ("curves=master='0/0 0.18/0.12 0.45/0.38 0.75/0.70 1/0.97',"
         "colorbalance=rs=-0.04:gs=0.0:bs=0.07:rm=-0.02:gm=0.0:bm=0.03:rh=0.03:gh=0.01:bh=-0.02,"
         "eq=saturation=0.86,vignette=PI/5")
GRAIN = "noise=alls=3:allf=t+u"


def encode(name, gdir, cdir, wav, fade_in):
    out = os.path.join(OUT, name + ".mp4")
    fin = "fade=t=in:st=0:d=0.8," if fade_in else ""
    fc = ("[0:v]scale=%d:%d:flags=lanczos,%s%s,%s,format=yuv420p[g];[1:v]%s,format=yuv420p[c];[g][c]concat=n=2:v=1:a=0[v]"
          % (W, H, fin, GRADE, GRAIN, GRAIN))
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-framerate", str(FPS), "-i", os.path.join(gdir, "%05d.png"),
           "-framerate", str(FPS), "-i", os.path.join(cdir, "%05d.png"),
           "-i", wav, "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "14M", "-bufsize", "28M",
           "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    log("wrote", out, "%.1f MB" % (os.path.getsize(out) / 1e6))
    return out


def stills(video, tag, times):
    for i, t in enumerate(times):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % t, "-i", video, "-frames:v", "1", "-q:v", "3",
                        os.path.join(OUT, "still_%s_%02d.jpg" % (tag, i))], check=True)


def main():
    plate = os.path.join(B, "frames", "f_%04d.png" % (shot("veranda")["f0"] + 30))
    full_shots = [s["name"] for s in SHOTS if s["f0"] < 1000]
    short_shots = [s["name"] for s in SHOTS if s["f0"] >= 1000]
    # full trailer: slow dips between the opening shots, hard cuts once she starts coming
    g, c, ng, nc = build_sequence("full", full_shots, {"ext", "veranda", "class", "feet", "corridor"}, 1.0, 7.5, plate)
    total = (ng + nc) / FPS
    write_wav(mix(score_full(total), total), os.path.join(B, "full.wav"))
    v = encode("moulika_trailer", g, c, os.path.join(B, "full.wav"), True)
    stills(v, "full", [2.0, 10.0, 17.0, 21.5, 29.5, 32.0, 36.6, 41.5])
    g, c, ng, nc = build_sequence("short", short_shots, {"s_walk"}, 0.8, 6.0, plate)
    total = (ng + nc) / FPS
    write_wav(mix(score_short(total), total), os.path.join(B, "short.wav"))
    v = encode("moulika_short_trailer", g, c, os.path.join(B, "short.wav"), True)
    stills(v, "short", [2.5, 6.5, 9.95, 10.2, 15.5])


main()
