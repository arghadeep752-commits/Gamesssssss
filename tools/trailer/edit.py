"""Cut the trailer: rendered shots + title cards + overlays + grade + soundtrack -> Chaya_Trailer.mp4

    python3 tools/trailer/edit.py <shots.mp4 (all rendered frames)> <soundtrack.wav> <out dir> <font.ttf> <devanagari.ttf> <logo.png>

Alight-Motion style finishing done with ffmpeg: flicker-in titles, RGB-split glitches on the scares, camera shake on
the jumpscare, white flash into the title, letterbox, teal/orange grade, vignette and film grain.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tl  # noqa: E402

SHOTS_MP4, AUDIO, OUT, FONT, DEVA, LOGO = (os.path.abspath(a) for a in sys.argv[1:7])
W, H = 1920, 1080
BAR = 138                                    # 2.39:1 letterbox
T = tl.load()
FPS = T["fps"]
EV = T["events"]
WORK = os.path.join(OUT, "work")
os.makedirs(WORK, exist_ok=True)


def run(cmd):
    print("+", " ".join(cmd if len(" ".join(cmd)) < 600 else cmd[:6] + ["..."]), flush=True)
    subprocess.run(cmd, check=True)


# ------------------------------------------------------------------------------------------------ text plates
def text_layer(lines):
    """lines: list of dict(text, size, y (0..1 of H), color, glow, spacing, font, glow_r)"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for ln in lines:
        font = ImageFont.truetype(ln.get("font", FONT), ln["size"])
        sp = ln.get("spacing", 0)
        txt = ln["text"]
        if sp:
            widths = [font.getlength(c) for c in txt]
            total = sum(widths) + sp * (len(txt) - 1)
        else:
            total = font.getlength(txt)
        x0 = (W - total) / 2.0
        asc, desc = font.getmetrics()
        y0 = ln["y"] * H - (asc + desc) / 2.0

        def draw(d, fill, stroke=0):
            kw = dict(font=font, fill=fill, stroke_width=stroke, stroke_fill=fill) if stroke else dict(font=font, fill=fill)
            if sp:
                x = x0
                for c, w_ in zip(txt, widths):
                    d.text((x, y0), c, **kw)
                    x += w_ + sp
            else:
                d.text((x0, y0), txt, **kw)
        if ln.get("glow"):
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw(ImageDraw.Draw(g), ln["glow"] + (255,))
            g = g.filter(ImageFilter.GaussianBlur(ln.get("glow_r", 14)))
            for _ in range(ln.get("glow_n", 2)):
                img = Image.alpha_composite(img, g)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), (0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(3))
        img = Image.alpha_composite(img, sh)
        fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw(ImageDraw.Draw(fg), ln.get("color", (236, 226, 210)) + (255,), ln.get("stroke", max(1, ln["size"] // 40)))
        img = Image.alpha_composite(img, fg)
    return img


def plate(name, lines, logo=None):
    img = text_layer(lines)
    if logo is not None:
        lg = Image.open(LOGO).convert("RGBA")
        w = logo["w"]
        lg = lg.resize((w, int(lg.height * w / lg.width)), Image.LANCZOS)
        img.alpha_composite(lg, (int((W - lg.width) / 2), int(logo["y"] * H - lg.height / 2)))
    p = os.path.join(WORK, name + ".png")
    img.save(p)
    return p


BONE = (236, 226, 210)
BLOOD = (150, 6, 4)
EMBER = (255, 120, 40)


def card_lines(e):
    st = e.get("style", "")
    if st == "studio":
        return [dict(text=e["lines"][0], size=92, y=0.47, spacing=6, glow=BLOOD, glow_r=18),
                dict(text=e["lines"][1], size=34, y=0.57, spacing=14, color=(200, 190, 175))]
    return [dict(text=e["lines"][0], size=88, y=0.5, spacing=5, glow=BLOOD, glow_r=20, glow_n=3)]


# ------------------------------------------------------------------------------------------------ segments
segs = T["segs"]
parts = []


def flicker_enable(t0, t_end):
    """overlay switched on like a failing bulb, then steady until t_end"""
    on = [(t0, t0 + 0.05), (t0 + 0.12, t0 + 0.16), (t0 + 0.24, t0 + 0.27)]
    expr = "+".join("between(t,%.3f,%.3f)" % ab for ab in on)
    return "%s+between(t,%.3f,%.3f)" % (expr, t0 + 0.34, t_end)


def encode(out, inputs, graph, last, dur):
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", graph, "-map", "[%s]" % last, "-t", "%.4f" % dur,
                                                         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "14",
                                                         "-pix_fmt", "yuv420p", out]
    run(cmd)


for k, e in enumerate(segs):
    out = os.path.join(WORK, "seg_%02d.mp4" % k)
    dur = e["dur"]
    if e["type"] in ("card", "black"):
        inputs = ["-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d:d=%.4f" % (W, H, FPS, dur)]
        g = "[0:v]format=yuv420p[b0]"
        last = "b0"
        if e["type"] == "card":
            st = e.get("style", "")
            if st == "end":
                L_ = e["lines"]
                items = [
                    ("end_logo", [], dict(w=560, y=0.29), 0.2),
                    ("end_l0", [dict(text=L_[0], size=74, y=0.52, spacing=5, glow=BLOOD, glow_r=16)], None, 0.9),
                    ("end_l1", [dict(text=L_[1], size=42, y=0.6, spacing=4, color=(205, 195, 180))], None, 1.5),
                    ("end_l2", [dict(text=L_[2], size=58, y=0.71, spacing=4, color=(255, 170, 90), glow=(190, 40, 0), glow_r=14)], None, 2.2),
                    ("end_l3", [dict(text=L_[3], size=34, y=0.785, spacing=10, color=(190, 180, 165))], None, 2.8),
                ]
                for i, (nm, lines, logo, t0) in enumerate(items):
                    p = plate(nm, lines, logo)
                    inputs += ["-loop", "1", "-t", "%.4f" % dur, "-i", p]
                    g += (";[%d:v]format=rgba,fade=t=in:st=%.3f:d=0.6:alpha=1,fade=t=out:st=%.3f:d=0.6:alpha=1[t%d]"
                          % (i + 1, t0, dur - 0.7, i))
                    g += ";[%s][t%d]overlay=0:0[b%d]" % (last, i, i + 1)
                    last = "b%d" % (i + 1)
            else:
                p = plate("card_%s" % e["seg"], card_lines(e))
                inputs += ["-loop", "1", "-t", "%.4f" % dur, "-i", p]
                t_in = 0.12 if st != "studio" else 0.5
                g += ";[1:v]format=rgba,fade=t=out:st=%.3f:d=0.35:alpha=1[t0]" % (dur - 0.45)
                g += ";[b0][t0]overlay=0:0:enable='%s'[b1]" % flicker_enable(t_in, dur)
                g += ";[b1]rgbashift=rh=-9:bh=9:enable='between(t,%.3f,%.3f)'[b2]" % (t_in, t_in + 0.3)
                last = "b2"
        encode(out, inputs, g, last, dur)
    else:
        a, b = e["f0"] - 1, e["f1"]
        inputs = ["-i", SHOTS_MP4]
        g = "[0:v]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS,scale=%d:%d:flags=lanczos,format=yuv420p[v0]" % (a, b, W, H)
        last = "v0"
        n = 0

        def chain(f):
            global g, last, n
            n += 1
            g += ";[%s]%s[v%d]" % (last, f, n)
            last = "v%d" % n
        sid = e["seg"]
        rel = lambda fr: (fr - e["f0"]) / float(FPS)      # noqa: E731
        if sid == "S1":
            chain("fade=t=in:st=0:d=0.7")
        if sid == "S4":
            for jf in (EV["s4_jump1"], EV["s4_jump2"]):
                x = rel(jf) - 0.05
                chain("rgbashift=rh=16:bh=-16:gv=4:enable='between(t,%.3f,%.3f)'" % (x, x + 0.17))
                chain("noise=alls=45:allf=t:enable='between(t,%.3f,%.3f)'" % (x, x + 0.17))
        if sid == "S5":
            x = rel(EV["s5_lamps_die"]) - 0.1
            chain("rgbashift=rh=10:bh=-10:enable='between(t,%.3f,%.3f)'" % (x, x + 0.25))
        if sid == "S7":
            x0 = rel(EV["s7_lunge"])
            x1 = rel(EV["s7_black"])
            sh = "between(t,%.3f,%.3f)" % (x0, x1)
            chain("crop=w=%d:h=%d:x='%d+%d*sin(n*2.1)*%s':y='%d+%d*cos(n*2.9)*%s'"
                  % (W - 96, H - 54, 48, 44, sh, 27, 24, sh))
            chain("scale=%d:%d" % (W, H))
            chain("rgbashift=rh=-18:bh=18:rv=6:enable='%s'" % sh)
            chain("noise=alls=30:allf=t:enable='%s'" % sh)
        if sid == "S6":
            chain("fade=t=out:st=%.3f:d=0.25" % (dur - 0.3))
        if sid == "S8":
            chain("fade=t=in:st=0:d=0.45:color=white")
            chain("fade=t=out:st=%.3f:d=0.6" % (dur - 0.65))
        for i, ov in enumerate(e.get("overlays", [])):
            st = ov.get("style", "")
            if st == "hindi":
                lines = [dict(text=ov["text"], size=78, y=0.745, font=DEVA, color=(235, 170, 70), glow=(170, 40, 0), glow_r=12)]
            elif st == "date":
                lines = [dict(text=ov["text"], size=50, y=0.835, spacing=8, color=BONE, glow=(120, 10, 0), glow_r=10)]
            else:
                lines = [dict(text=ov["text"], size=58, y=0.8, spacing=5, color=BONE, glow=BLOOD, glow_r=12)]
            p = plate("ov_%s_%d" % (sid, i), lines)
            inputs += ["-loop", "1", "-t", "%.4f" % dur, "-i", p]
            t0, t1 = ov["t0"], min(ov["t1"], dur)
            g += (";[%d:v]format=rgba,fade=t=in:st=%.3f:d=0.5:alpha=1,fade=t=out:st=%.3f:d=0.45:alpha=1[o%d]"
                  % (i + 1, t0, max(t0 + 0.5, t1 - 0.45), i))
            n += 1
            g += ";[%s][o%d]overlay=0:0:enable='between(t,%.3f,%.3f)'[v%d]" % (last, i, t0, t1, n)
            last = "v%d" % n
        encode(out, inputs, g, last, dur)
    parts.append(out)

# ------------------------------------------------------------------------------------------------ final: grade, letterbox, grain, sound
lst = os.path.join(WORK, "list.txt")
open(lst, "w").write("".join("file '%s'\n" % p for p in parts))
grade = ",".join([
    "eq=contrast=1.07:saturation=0.9:gamma=0.97",
    "colorbalance=rs=-0.03:gs=0.005:bs=0.045:rh=0.05:gh=0.01:bh=-0.05",
    "vignette=angle=PI/4.6",
    "noise=alls=5:allf=t+u",
    "drawbox=x=0:y=0:w=iw:h=%d:color=black:t=fill" % BAR,
    "drawbox=x=0:y=ih-%d:w=iw:h=%d:color=black:t=fill" % (BAR, BAR),
    "format=yuv420p",
])
final = os.path.join(OUT, "Chaya_Trailer.mp4")
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", AUDIO,
     "-filter_complex", "[0:v]%s[v]" % grade, "-map", "[v]", "-map", "1:a",
     "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
     "-r", str(FPS), "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart",
     "-t", "%.3f" % T["total"], final])
# a poster frame (the title) and a no-text version for re-editing (e.g. in Alight Motion)
t_poster = tl.when(T, "S8", 4.6)
run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t_poster, "-i", final, "-frames:v", "1", "-q:v", "2", os.path.join(OUT, "Chaya_Trailer_poster.jpg")])
run(["ffmpeg", "-v", "error", "-y", "-i", SHOTS_MP4, "-vf", "scale=%d:%d:flags=lanczos" % (W, H), "-c:v", "libx264", "-preset", "medium",
     "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), os.path.join(OUT, "Chaya_Trailer_raw_shots.mp4")])
print("trailer:", final, "%.2fs" % T["total"])
