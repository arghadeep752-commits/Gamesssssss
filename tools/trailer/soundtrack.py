"""Trailer soundtrack: mixed only from real recordings (the game's Commons sounds + tools/trailer/fetch_sfx.py).

    python3 tools/trailer/soundtrack.py <game sounds dir> <trailer sounds dir> <out dir>

Nothing is synthesised: every layer is a recording, at most slowed / reversed / filtered / echoed with ffmpeg.
Writes <out>/trailer_mix.wav (final), <out>/music_bed.wav and <out>/sfx.wav (stems for re-editing) and cues.txt.
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tl  # noqa: E402

GAME, TSND, OUT = (os.path.abspath(a) for a in sys.argv[1:4])
os.makedirs(OUT, exist_ok=True)
SR = 48000
T = tl.load()
EV = T["events"]
DUR = T["total"]
CUES = []


def at(seg, off=0.0):
    return tl.when(T, seg, off)


def fr(seg, frame):
    return tl.shot_time(T, seg, frame)


def find(*names):
    for n in names:
        for d in (TSND, GAME):
            p = os.path.join(d, n + ".ogg")
            if os.path.exists(p):
                return p
    return None


def load(names, af=None):
    """first existing recording of `names` (str or tuple), decoded to mono 48 kHz, through an ffmpeg filter chain"""
    names = (names,) if isinstance(names, str) else names
    p = find(*names)
    if p is None:
        print("missing sound:", names)
        return None
    cmd = ["ffmpeg", "-v", "error", "-i", p]
    if af:
        cmd += ["-af", af]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()
    return x if len(x) else None


ECHO = "apad=pad_dur=%g,aecho=0.8:0.55:%s:%s"
SRC_SR = 44100                               # the recordings were all stored at 44.1 kHz


def slow(ratio):
    """tape-style speed change (pitch and tempo together), like slowing a reel"""
    return "aresample=%d,asetrate=%d,aresample=%d" % (SRC_SR, int(round(SRC_SR * ratio)), SR)


def echo(tail=2.0, delays="70|150|290|520", decays="0.45|0.32|0.2|0.12"):
    return ECHO % (tail, delays, decays)


class Bus:
    def __init__(self):
        self.b = np.zeros((2, int((DUR + 2.0) * SR)), np.float32)

    def add(self, x, t, gain_db=0.0, pan=0.0, fade_in=0.0, fade_out=0.0, length=None, label=""):
        if x is None or t >= DUR:
            return
        x = x.astype(np.float32)
        if length is not None:
            n = int(length * SR)
            if len(x) < n:
                x = np.tile(x, n // max(1, len(x)) + 1)
            x = x[:n].copy()
        else:
            x = x.copy()
        i0 = int(round(t * SR))
        if i0 < 0:
            x = x[-i0:]
            i0 = 0
        x = x[: max(0, self.b.shape[1] - i0)]
        if not len(x):
            return
        fi, fo = int(fade_in * SR), int(fade_out * SR)
        if fi > 0:
            x[:fi] *= np.linspace(0, 1, min(fi, len(x)), dtype=np.float32)[: len(x[:fi])]
        if fo > 0:
            k = min(fo, len(x))
            x[-k:] *= np.linspace(1, 0, k, dtype=np.float32)
        g = 10 ** (gain_db / 20.0)
        a = (pan + 1) * np.pi / 4
        self.b[0, i0:i0 + len(x)] += x * g * np.cos(a)
        self.b[1, i0:i0 + len(x)] += x * g * np.sin(a)
        CUES.append("%7.2fs  %-6.1fdB  %s" % (t, gain_db, label))

    def mute(self, t0, t1, fade=0.03):
        i0, i1, f = int(t0 * SR), int(t1 * SR), int(fade * SR)
        env = np.ones(self.b.shape[1], np.float32)
        env[i0:i1] = 0.0
        env[max(0, i0 - f):i0] = np.linspace(1, 0, i0 - max(0, i0 - f), dtype=np.float32)
        env[i1:i1 + f] = np.linspace(0, 1, len(env[i1:i1 + f]), dtype=np.float32)
        self.b *= env


music, sfx = Bus(), Bus()
TOTAL = DUR

# ------------------------------------------------------------------------------------------------ beds (music)
drone_lo = load(("tanpura", "menu_drone"), slow(0.75) + ",lowpass=f=1600")
drone_dark = load("menu_drone", slow(0.8) + ",lowpass=f=1100")
tanpura = load(("tanpura",), "lowpass=f=5000")
chant = load(("chant", "ritual_chant"), slow(0.92) + ",lowpass=f=3500," + echo(2.5))
wind = load(("wind", "ambient"), "lowpass=f=2500")
s6_end = at("S6", T["by_id"]["S6"]["dur"])
music.add(drone_dark, 0.0, -21, 0.0, 2.5, 1.0, s6_end - 0.0, "dark drone")
music.add(drone_lo, 0.6, -23, 0.0, 3.0, 1.2, s6_end - 0.6, "low tanpura drone")
music.add(tanpura, at("S3", 0.0), -20, -0.3, 1.0, 1.5, 5.5, "tanpura (pooja)")
music.add(chant, at("S3", 0.2), -15, 0.25, 1.2, 1.6, 5.4, "chant (pooja)")
music.add(drone_dark, at("S8", 0.0), -16, 0.0, 0.05, 3.5, TOTAL - at("S8", 0.0), "title drone")
music.add(drone_lo, at("S8", 0.3), -18, 0.0, 1.5, 3.5, TOTAL - at("S8", 0.3), "title tanpura")
sfx.add(wind, 0.0, -28, 0.0, 2.0, 2.0, s6_end, "wind")

# ------------------------------------------------------------------------------------------------ hits & stingers
boom = load("boom", slow(0.62) + ",lowpass=f=900," + echo(3.0, "90|210|400|700", "0.5|0.35|0.22|0.12"))
boom_hi = load("boom", echo(2.0))
thunder = load(("thunder", "ritual_end"), "lowpass=f=4000")
cym_rev = load(("cymbal", "menu_start"), "areverse,lowpass=f=7000")
cym = load(("cymbal", "menu_start"), echo(1.5))
dhol = load("dhol", "lowpass=f=2500," + echo(1.5))
conch = load(("conch",), slow(0.94) + "," + echo(3.0, "120|260|480|800", "0.5|0.36|0.24|0.14"))
gong = load("menu_start", echo(2.5))


def hit(t, big=1.0, label="hit"):
    sfx.add(boom, t, -3 + 3 * (big - 1), 0.0, 0.0, 0.5, None, label + " boom")
    sfx.add(boom_hi, t, -10, 0.0, 0.0, 0.4, None, label + " drum")
    if big >= 1.0:
        sfx.add(thunder, t + 0.05, -12, 0.0, 0.01, 2.0, 5.0, label + " thunder tail")


def riser(t_end, length=2.0, gain=-8, label="riser"):
    if cym_rev is None:
        return
    x = cym_rev[-int(length * SR):] if len(cym_rev) > length * SR else cym_rev
    sfx.add(x, t_end - len(x) / SR, gain, 0.0, 0.3, 0.02, None, label)


sfx.add(boom, 0.25, -6, 0.0, 0.0, 1.0, None, "opening boom")
riser(at("S1"), 1.8, -12, "into S1")
hit(at("cardA"), 1.0, "card A")
hit(at("cardB"), 1.0, "card B")
hit(at("cardC"), 1.0, "card C")
riser(at("S4"), 1.4, -10, "into S4")
sfx.add(dhol, at("cardA", 0.0), -14, -0.2, 0.0, 1.0, 1.7, "dhol A")
sfx.add(dhol, at("cardB", 0.0), -14, 0.2, 0.0, 1.0, 1.7, "dhol B")

# ------------------------------------------------------------------------------------------------ S1
buzz = load(("buzz",), "highpass=f=80")
f0, f1 = EV["s1_flicker"]
if buzz is not None:
    gate_t = fr("S1", f0)
    n = int((fr("S1", f1) - gate_t) * SR)
    x = np.tile(buzz, n // max(1, len(buzz)) + 1)[:n].copy()
    rng = np.random.default_rng(5)
    seg = SR // 12
    for k in range(0, n, seg):
        x[k:k + seg] *= 1.0 if rng.random() > 0.4 else 0.05
    sfx.add(x, gate_t, -15, 0.15, 0.05, 0.1, None, "lantern buzz")
whisper = load(("ghost_whisper", "whisper_far"), echo(2.0))
sfx.add(whisper, fr("S1", EV["s1_figure"][0]), -13, -0.4, 0.3, 1.0, 2.6, "whisper (figure)")
creak = load(("creak", "door_close"), "lowpass=f=3000")
sfx.add(creak, at("S1", 0.8), -20, 0.5, 0.05, 0.5, 2.0, "floor creak")

# ------------------------------------------------------------------------------------------------ S2
steps = [load("footstep_%d" % k, "lowpass=f=2400") for k in range(1, 6)]
walk_end = EV["s2_walk_end"]
s2_0 = at("S2")
walk_len = (walk_end - T["by_id"]["S2"]["f0"]) / float(T["fps"])
for k, u in enumerate((0.1, 0.32, 0.53, 0.73, 0.92)):
    sfx.add(steps[k % len(steps)], s2_0 + u * walk_len, -12 - k * 0.8, -0.1 + 0.2 * (k % 2), 0.0, 0.05, None, "footstep")
door = load(("door_open", "door_close"), slow(0.78) + ",lowpass=f=5000," + echo(1.5))
sfx.add(door, fr("S2", EV["s2_door"][0]), -7, -0.2, 0.05, 1.0, None, "door creak")
heart = load(("heartbeat",), "lowpass=f=900")
sfx.add(heart, fr("S2", EV["s2_door"][0] + 30), -15, 0.0, 1.5, 0.3, at("cardB") - fr("S2", EV["s2_door"][0] + 30), "heartbeat (door)")
riser(at("cardB"), 2.2, -9, "reveal riser")
breath = load(("breath",), "lowpass=f=3000," + echo(1.0))
sfx.add(breath, fr("S2", EV["s2_door"][0] + 50), -18, 0.3, 0.4, 0.6, 2.2, "her breath")

# ------------------------------------------------------------------------------------------------ S3 pooja
bell = load(("bell", "pickup"), echo(3.0, "110|240|430|700", "0.5|0.35|0.22|0.12"))
sfx.add(bell, at("S3", 0.1), -9, -0.25, 0.0, 1.2, 3.0, "temple bell 1")
sfx.add(bell, at("S3", 2.6), -11, 0.25, 0.0, 1.5, 2.6, "temple bell 2")
fire = load(("fire",), "lowpass=f=6000")
sfx.add(fire, at("S3", 0.0), -24, 0.0, 0.8, 0.8, 5.0, "diya flames")

# ------------------------------------------------------------------------------------------------ S4 corridor
heart_fast = load(("heartbeat",), slow(1.18) + ",lowpass=f=900")
sfx.add(heart, at("S4", 0.0), -12, 0.0, 0.5, 0.2, T["by_id"]["S4"]["dur"], "heartbeat")
whoosh = load(("whoosh",), echo(1.0))
for jf in (EV["s4_jump1"], EV["s4_jump2"]):
    tj = fr("S4", jf)
    if buzz is not None:
        sfx.add(buzz, tj - 0.12, -9, 0.0, 0.0, 0.05, 0.28, "lamp short")
    sfx.add(boom, tj, -4, 0.0, 0.0, 0.6, None, "jump boom")
    sfx.add(whoosh, tj - 0.05, -10, -0.3, 0.0, 0.3, None, "jump whoosh")
sfx.add(dhol, at("S4", 0.5), -20, 0.0, 1.0, 1.0, 4.5, "ritual drum under S4")

# ------------------------------------------------------------------------------------------------ S5 she walks
ghung = load(("ghungroo",), "highpass=f=400," + echo(1.2, "60|140|260", "0.4|0.25|0.12"))
s5 = at("S5")
for k in range(9):
    sfx.add(ghung, s5 + 0.25 + k * 0.56, -13 + 0.5 * k, 0.15 * ((-1) ** k), 0.0, 0.25, 0.5, "anklet step")
sfx.add(heart_fast, s5, -11, 0.0, 0.2, 0.1, T["by_id"]["S5"]["dur"] + T["by_id"]["S6"]["dur"], "heartbeat fast")
riser(fr("S5", EV["s5_lamps_die"]), 3.0, -7, "S5 riser")
sfx.add(boom, fr("S5", EV["s5_lamps_die"]), -6, 0.0, 0.0, 0.8, None, "lamps die")
if buzz is not None:
    sfx.add(buzz, fr("S5", EV["s5_lamps_die"]) - 0.4, -12, 0.0, 0.05, 0.02, 0.4, "lamps buzz out")

# ------------------------------------------------------------------------------------------------ S6 candle dies, silence, S7 jumpscare
blow = load(("blowout", "whoosh"), "lowpass=f=5000")
t_die = fr("S6", EV["s6_die"])
sfx.add(fire, at("S6", 0.0), -22, 0.0, 0.2, 0.2, t_die - at("S6", 0.0), "candle")
sfx.add(blow, t_die - 0.05, -6, 0.0, 0.0, 0.3, None, "candle blown out")
t_lunge = fr("S7", EV["s7_lunge"])
t_black = fr("S7", EV["s7_black"])
music.mute(t_die + 0.35, t_lunge - 0.02, 0.4)
sfx.mute(t_die + 0.6, t_lunge - 0.02, 0.3)
scream = load(("jumpscare", "scream"), "highpass=f=120")
scream2 = load(("scream", "jumpscare"), slow(0.85))
sfx.add(scream, t_lunge, 1.0, 0.0, 0.0, 0.3, None, "SCREAM")
sfx.add(scream2, t_lunge + 0.02, -5, 0.0, 0.0, 0.3, None, "scream layer")
sfx.add(boom, t_lunge, 0.0, 0.0, 0.0, 0.3, None, "jumpscare boom")
sfx.add(cym, t_lunge, -6, 0.0, 0.0, 0.3, None, "jumpscare crash")
if buzz is not None:
    sfx.add(buzz, t_lunge, -8, 0.0, 0.0, 0.05, t_black - t_lunge, "strobe buzz")
music.mute(t_black, at("S8") - 0.01, 0.05)
sfx.mute(t_black, at("S8") - 0.01, 0.05)

# ------------------------------------------------------------------------------------------------ S8 title, end card
t8 = at("S8")
hit(t8, 1.4, "TITLE")
sfx.add(gong, t8 + 0.02, -8, 0.0, 0.0, 2.0, None, "title gong")
sfx.add(conch, t8 + 0.35, -5, 0.0, 0.15, 1.5, 4.5, "conch (shankh)")
sfx.add(fire, t8 + 0.2, -18, 0.0, 1.0, 2.0, TOTAL - t8 - 0.2, "fire")
hit(at("end"), 0.6, "end card")
sfx.add(whisper, at("end", 1.5), -12, 0.3, 0.4, 1.2, 3.0, "whisper (end)")
sfx.add(ghung, TOTAL - 1.1, -12, -0.4, 0.0, 0.8, 0.9, "last anklet")

# ------------------------------------------------------------------------------------------------ write
def write(name, b):
    b = b[:, : int(TOTAL * SR)]
    pcm = np.clip(b.T, -1.0, 1.0)
    raw = os.path.join(OUT, name + ".f32")
    pcm.astype("<f4").tofile(raw)
    return raw


def render(raw, out_wav, norm=True):
    """two-pass EBU R128 loudness to -14 LUFS (linear gain, the dynamics stay), or just a safety limiter"""
    src = ["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw]
    af = "alimiter=limit=0.95:level=disabled"
    if norm:
        target = "I=-14:TP=-1.0:LRA=20"
        m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + src + ["-af", "loudnorm=%s:print_format=json" % target, "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        try:
            j = json.loads(m[m.rindex("{"): m.rindex("}") + 1])
            af = ("loudnorm=%s:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
                  % (target, j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
            print("loudness in:", j["input_i"], "LUFS, true peak", j["input_tp"])
        except Exception as ex:     # noqa: BLE001
            print("loudness measure failed:", ex)
            af = "loudnorm=%s" % target
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + src + ["-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", out_wav], check=True)
    os.remove(raw)


peak = float(np.max(np.abs(music.b + sfx.b))) + 1e-9
scale = 0.9 / peak
render(write("mixraw", (music.b + sfx.b) * scale), os.path.join(OUT, "trailer_mix.wav"))
render(write("musicraw", music.b * scale), os.path.join(OUT, "music_bed.wav"), norm=False)
render(write("sfxraw", sfx.b * scale), os.path.join(OUT, "sfx.wav"), norm=False)
open(os.path.join(OUT, "cues.txt"), "w").write("\n".join(sorted(CUES)) + "\n")
print("\n".join(sorted(CUES)))
print("soundtrack: %.2fs" % TOTAL)
