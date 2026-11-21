#!/usr/bin/env python3
"""Score + sound design mix for the trailer.
Music: Adobe Stock "Emotional Epic Violin (With Choir)" (violinchoir) and
"Wizard (Cinematic | Epic Trailer Music)" (wizard), re-edited to the cut.
SFX: synthesised conch (shankh), booms, risers, whooshes, tanpura drone + stock temple bells & wind.
Usage: audio.py <audio_dir> <out.wav>"""
import subprocess, sys
import numpy as np
from scipy import signal

SR = 48000
TOTAL = 158.5
rng = np.random.default_rng(42)


def load(path, mono=False):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1" if mono else "2", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32)
    return a if mono else a.reshape(-1, 2)


def db(x):
    return 10 ** (x / 20.0)


def fade(n, fin, fout):
    e = np.ones(n, np.float32)
    a, b = int(fin * SR), int(fout * SR)
    if a > 0:
        e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if b > 0:
        e[-b:] = np.minimum(e[-b:], np.cos(np.linspace(0, np.pi / 2, b)) ** 2)
    return e


class Bus:
    def __init__(self):
        self.x = np.zeros((int(TOTAL * SR) + SR, 2), np.float32)

    def add(self, sig, at, gain_db=0.0, pan=0.0):
        if sig.ndim == 1:
            l = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
            r = np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
            sig = np.stack([sig * l, sig * r], 1)
        i = int(at * SR)
        if i >= len(self.x):
            return
        n = min(len(sig), len(self.x) - i)
        self.x[i:i + n] += sig[:n] * db(gain_db)


def seg(track, a, b, fin=0.05, fout=0.05):
    s = track[int(a * SR):int(b * SR)].copy()
    return s * fade(len(s), fin, fout)[:, None]


# ---------------------------------------------------------------- DSP helpers
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, btype="high", fs=SR, output="sos"), x, axis=0)


def reverb(x, rt60=2.8, wet=0.35, pre=0.02, bright=6000):
    n = int(rt60 * SR)
    t = np.arange(n) / SR
    irs = []
    for ch in range(2):
        nz = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
        nz = lp(nz, bright)
        nz[: int(pre * SR)] = 0
        irs.append(nz / np.sqrt(np.sum(nz ** 2)))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    out = np.zeros((len(x) + n - 1, 2), np.float32)
    for ch in range(2):
        out[:, ch] = signal.fftconvolve(x[:, ch], irs[ch])
    dry = np.zeros_like(out)
    dry[: len(x)] = x
    return dry * (1 - wet) + out * wet * 1.8


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


# ---------------------------------------------------------------- instruments
def conch(dur=2.6, f0=369.99, power=1.0):
    """Shankh: brassy horn with breath, pitch scoop, slight vibrato and release fall."""
    t = np.arange(int(dur * SR)) / SR
    scoop = 0.9 + 0.1 * (1 - np.exp(-t / 0.06))
    fall = 1 - 0.035 * np.clip((t - (dur - 0.45)) / 0.45, 0, 1) ** 2
    vib = 1 + 0.005 * np.sin(2 * np.pi * 5.4 * t + 0.6) * np.clip((t - 0.25) / 0.5, 0, 1)
    f = f0 * scoop * fall * vib
    ph = 2 * np.pi * np.cumsum(f) / SR
    bright = 0.55 + 0.45 * np.clip(t / 0.35, 0, 1) * power
    sig = np.zeros_like(t)
    for n in range(1, 22):
        a = (1.0 / n ** 1.05) * (1.0 if n % 2 else 0.75) * (bright ** (0.15 * n))
        sig += a * np.sin(n * ph + 0.37 * n)
    # body resonances (formants)
    form = bp(sig, 650, 1100) * 1.6 + bp(sig, 2100, 3200) * 0.8 + bp(sig, 200, 650) * 0.9
    breath = bp(rng.standard_normal(len(t)), 900, 4200) * 0.07 * (0.6 + 0.4 * np.clip(t / 0.2, 0, 1))
    env = np.clip(t / 0.09, 0, 1) ** 1.5 * (1 - np.clip((t - (dur - 0.35)) / 0.35, 0, 1))
    out = (form + breath) * env
    return norm(out, 0.8)


def conch_pair(dur=2.8):
    a = conch(dur, 369.99)
    b = conch(dur * 0.98, 184.997, 0.8)  # octave below for weight
    n = min(len(a), len(b))
    return norm(a[:n] + 0.55 * b[:n], 0.85)


def boom(dur=3.5, low=28, high=72, punch=1.0):
    t = np.arange(int(dur * SR)) / SR
    f = (high - low) * np.exp(-t / 0.22) + low
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.1)
    body = lp(rng.standard_normal(len(t)), 220) * np.exp(-t / 0.32) * 2.2
    click = lp(rng.standard_normal(len(t)), 3500) * np.exp(-t / 0.012) * 0.6 * punch
    sig = sub * 1.0 + body * 0.45 + click
    return norm(reverb(sig, 2.6, 0.3), 0.95)


def riser(dur=3.0, end_pitch=4.0):
    t = np.arange(int(dur * SR)) / SR
    k = t / dur
    nz = rng.standard_normal(len(t))
    out = np.zeros_like(t)
    # swept band-passed noise (time-varying filter done in blocks)
    blk = 2048
    for i in range(0, len(t), blk):
        c = 300 * (20 ** k[i])
        out[i:i + blk] = bp(nz[i:i + blk], max(60, c * 0.6), min(SR / 2 - 100, c * 1.5), 1)
    tone = np.zeros_like(t)
    for base in (110, 220, 440):
        ph = 2 * np.pi * np.cumsum(base * (end_pitch ** k)) / SR
        tone += np.sin(ph) * 0.25
    sig = (out * 0.9 + tone * 0.5) * (k ** 2.2)
    return norm(reverb(sig, 1.6, 0.25), 0.8)


def whoosh(dur=0.9, lo=300, hi=3500):
    t = np.arange(int(dur * SR)) / SR
    k = t / dur
    nz = rng.standard_normal(len(t))
    sig = bp(nz, lo, hi) * np.sin(np.pi * k) ** 2.5
    pan = np.linspace(-0.8, 0.8, len(t))
    st = np.stack([sig * np.cos((pan + 1) * np.pi / 4), sig * np.sin((pan + 1) * np.pi / 4)], 1)
    return norm(st, 0.7)


def rumble(dur=8.0):
    t = np.arange(int(dur * SR)) / SR
    sig = lp(rng.standard_normal(len(t)), 90) * 4 + np.sin(2 * np.pi * 36 * t) * 0.4
    return norm(sig * np.sin(np.pi * t / dur) ** 1.2, 0.7)


def tanpura(dur=26.0, sa=92.5):
    """F# tanpura drone: Pa(C#2) Sa'(F#3) Sa'(F#3) Sa(F#2) cycle with jawari brightness."""
    notes = [sa * 0.749, sa * 2, sa * 2, sa]
    out = np.zeros(int((dur + 6) * SR))
    period = 1.35
    k = 0
    while k * period < dur:
        f0 = notes[k % 4]
        t = np.arange(int(6 * SR)) / SR
        pl = np.zeros_like(t)
        for n in range(1, 24):
            bloom = np.exp(-((t - 0.5 - n * 0.02) ** 2) / 0.35) * 0.7 + 0.3
            pl += (1.0 / n) * bloom * np.sin(2 * np.pi * f0 * n * t * (1 + 0.0004 * n)) * np.exp(-t / (3.2 - n * 0.08))
        i = int(k * period * SR)
        out[i:i + len(pl)] += pl * np.clip(t / 0.01, 0, 1)
        k += 1
    out = out[: int(dur * SR)] * fade(int(dur * SR), 3.0, 4.0)
    return norm(reverb(out, 2.4, 0.35), 0.6)


def heartbeat(n=6, bpm=62):
    beat = 60 / bpm
    out = np.zeros(int((n * beat + 1) * SR))
    for i in range(n):
        for off, g in ((0, 1.0), (0.22, 0.7)):
            t = np.arange(int(0.35 * SR)) / SR
            th = np.sin(2 * np.pi * 52 * t) * np.exp(-t / 0.08) * g
            j = int((i * beat + off) * SR)
            out[j:j + len(th)] += th
    return norm(out, 0.8)


# ---------------------------------------------------------------- the mix
def build(audio_dir, out_path):
    vc = load(f"{audio_dir}/violinchoir.wav")
    wz = load(f"{audio_dir}/wizard.wav")
    bell = load(f"{audio_dir}/bell.wav")
    bell2 = load(f"{audio_dir}/bell2.wav")
    wind = load(f"{audio_dir}/wind.wav")

    music = Bus()
    # M1  opening -> Krishna arrival (violin + choir, F#)
    music.add(seg(vc, 0.0, 50.6, 2.5, 0.6), 0.0, 2.5)
    # M2  Gita dialogue (soft section)
    music.add(seg(vc, 74.0, 98.9, 0.6, 0.5), 50.3, 3.5)
    # M3  Vishwaroop climax (choir)
    music.add(seg(vc, 155.0, 180.4, 0.02, 0.35), 75.0, 2.0)
    # M4  Bhishma / wheel (percussive ostinato)
    music.add(seg(wz, 36.4, 61.45, 0.01, 0.3), 100.4, -2.0)
    # M5  Arjuna's plea (emotional outro strings)
    music.add(seg(vc, 183.5, 198.6, 0.5, 1.0), 125.6, 3.0)
    # M6  final reveal + title
    music.add(seg(wz, 189.2, 201.8, 0.01, 1.5), 141.6, -1.5)

    sfx = Bus()
    w = wind * fade(len(wind), 2.5, 3.0)[:, None]
    sfx.add(w[: int(17.5 * SR)] * fade(int(17.5 * SR), 2.0, 2.5)[:, None], 0.0, -9)
    sfx.add(w[int(4 * SR): int(22 * SR)] * fade(int(18 * SR), 1.5, 3.0)[:, None], 17.0, -20)
    sfx.add(rumble(9.0), 0.0, -8)
    c_far = reverb(conch(1.9, 369.99, 0.7), 3.8, 0.7)
    sfx.add(c_far, 1.5, -13, pan=-0.2)
    sfx.add(bell, 7.9, -10, pan=0.15)
    sfx.add(bell2, 40.1, -11, pan=-0.1)
    sfx.add(bell2, 67.6, -18, pan=0.2)
    sfx.add(tanpura(16.0), 0.5, -15)
    sfx.add(tanpura(25.5), 50.3, -13)
    for t0, g in ((16.9, -4), (50.0, -3), (75.0, -1), (100.4, -3), (125.4, -10)):
        sfx.add(boom(3.5), t0, g)
    sfx.add(riser(3.0), 72.0, -6)
    sfx.add(riser(2.6, 3.0), 97.8, -9)
    sfx.add(riser(3.2), 146.1, -7)
    sfx.add(whoosh(0.8), 13.1, -14)
    for t0 in (103.75, 104.15, 104.6, 105.0):
        sfx.add(whoosh(0.55, 600, 6000), t0 - 0.3, -10)
    for t0 in (108.3, 115.0, 117.7, 121.6):
        sfx.add(whoosh(0.7), t0 - 0.35, -12)
    sfx.add(heartbeat(4, 60), 136.4, -12)
    # final conch blast + title slams
    big = reverb(conch_pair(3.0), 4.2, 0.5)
    sfx.add(big, 141.6, -2.5)
    sfx.add(boom(4.0, 24, 80, 1.3), 141.6, -2)
    sfx.add(boom(5.0, 22, 70, 1.4), 149.3, -1)
    sfx.add(boom(4.5, 26, 60, 0.8), 152.2, -5)
    sfx.add(whoosh(1.2, 200, 2500), 147.0, -14)

    mix = music.x * 0.9 + sfx.x * 0.8
    # gentle master: soft clip + peak normalise
    mix = np.tanh(mix * 1.25) / np.tanh(1.25)
    mix = norm(mix[: int(TOTAL * SR)], db(-1.0))
    mix *= fade(len(mix), 0.0, 3.0)[:, None]
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(out_path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    print("wrote", out_path, len(mix) / SR, "s")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
