#!/usr/bin/env python3
"""Interface sounds made in code (keypad beeps, the PC's start-up chime, the power coming back on, menu ticks), plus
plain stand-ins for every recorded sound, used only when the download of the real recording failed.

    python3 tools/sounds/synth.py OUT_DIR
"""
import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(11)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.005, r=0.1):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lp(x, k):
    """One-pole low-pass (k small = darker)."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


def lp_fast(x, k):
    from math import exp  # noqa: F401
    # vectorised via exponential smoothing in chunks (good enough for noise beds)
    y = np.empty_like(x)
    acc = 0.0
    step = 4096
    for s in range(0, len(x), step):
        seg = x[s:s + step]
        out = np.empty_like(seg)
        for i in range(len(seg)):
            acc += k * (seg[i] - acc)
            out[i] = acc
        y[s:s + step] = out
    return y


def noise(n):
    return rng.standard_normal(n)


def norm(x, peak=0.85):
    m = float(np.max(np.abs(x))) or 1.0
    return (x / m * peak).astype(np.float32)


def save(out, name, x):
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, name + ".wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", "4", os.path.join(out, name + ".ogg")], check=True)
    os.remove(tmp)


def tone(f, sec, a=0.004, r=0.05, harm=(1.0,)):
    tt = t(sec)
    x = sum(h * np.sin(2 * np.pi * f * (k + 1) * tt) for k, h in enumerate(harm))
    return x * env(len(tt), a, r)


def mix(*xs):
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def thump(sec=0.25, f0=90, f1=40, noise_amt=0.3, dark=0.05):
    tt = t(sec)
    f = f1 + (f0 - f1) * np.exp(-tt * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-tt * 14)
    x += lp(noise(len(tt)), dark) * np.exp(-tt * 30) * noise_amt * 6
    return x


def click(sec=0.03, bright=0.5):
    tt = t(sec)
    return noise(len(tt)) * np.exp(-tt * 300) * bright + np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 200) * 0.4


def ui(out):
    save(out, "keypad_beep", norm(tone(1250, 0.09, r=0.04, harm=(1.0, 0.15)), 0.5))
    save(out, "keypad_ok", norm(np.concatenate([tone(1050, 0.1, r=0.03), tone(1580, 0.18, r=0.08)]), 0.55))
    save(out, "keypad_bad", norm(tone(180, 0.32, r=0.06, harm=(1.0, 0.6, 0.4, 0.3)), 0.6))
    chime = np.zeros(int(1.8 * SR))
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        s = int(k * 0.12 * SR)
        x = tone(f, 1.8 - k * 0.12, a=0.01, r=1.2, harm=(1.0, 0.25, 0.08))
        chime[s:s + len(x)] += x[: len(chime) - s]
    save(out, "pc_boot", norm(chime, 0.6))
    tt = t(2.2)
    hum = sum(np.sin(2 * np.pi * 50 * h * tt) / h for h in (1, 2, 3, 5)) * np.clip(tt / 1.2, 0, 1) * np.exp(-np.maximum(tt - 1.4, 0) * 3)
    x = hum * 0.5
    x[: int(0.25 * SR)] += thump(0.25, 120, 50, 0.5)
    save(out, "power_on", norm(x, 0.7))
    save(out, "ticker", norm(tone(1900, 0.03, r=0.02), 0.25))
    save(out, "ui_click", norm(click(0.04, 0.6), 0.5))


def stand_ins(out):
    for k in range(1, 7):
        x = mix(thump(0.22, 110 + rng.uniform(-15, 15), 55, 0.5, 0.08) * 0.7, click(0.02, 0.15))
        save(out, "footstep_%d" % k, norm(x, 0.7))
    tt = t(0.9)
    creak = np.sin(2 * np.pi * np.cumsum(220 + 60 * np.sin(2 * np.pi * 3 * tt)) / SR) * np.exp(-tt * 3) * 0.25
    save(out, "door_open", norm(lp(creak + noise(len(tt)) * 0.05 * np.exp(-tt * 6), 0.2), 0.6))
    x = thump(0.5, 80, 35, 0.8, 0.06)
    save(out, "door_close", norm(x, 0.8))
    x = np.concatenate([click(0.05, 0.8), np.zeros(int(0.08 * SR)), click(0.05, 0.8), np.zeros(int(0.06 * SR)), click(0.05, 0.6)])
    save(out, "door_locked", norm(x, 0.7))
    x = np.concatenate([click(0.04, 0.6), np.zeros(int(0.12 * SR)), click(0.06, 0.9)])
    save(out, "unlock", norm(x, 0.7))
    save(out, "padlock", norm(np.concatenate([click(0.06, 1.0), tone(2600, 0.25, r=0.2) * 0.2]), 0.7))
    tt = t(0.5)
    crack = noise(len(tt)) * np.exp(-tt * 20) + thump(0.5, 140, 60, 0.4) * 0.6
    save(out, "plank_crack", norm(crack, 0.8))
    save(out, "plank_fall", norm(thump(0.6, 100, 40, 1.0, 0.1), 0.8))
    jing = np.zeros(int(0.5 * SR))
    for _ in range(9):
        s = int(rng.uniform(0, 0.3) * SR)
        x = tone(rng.uniform(3000, 6000), 0.15, r=0.12) * rng.uniform(0.2, 0.5)
        jing[s:s + len(x)] += x[: len(jing) - s]
    save(out, "pickup", norm(jing, 0.5))
    tt = t(0.8)
    clang = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * d) for f, d in ((420, 6), (1130, 9), (2310, 12))) + click(0.8, 0.5)
    save(out, "drop", norm(clang, 0.7))
    save(out, "switch", norm(np.concatenate([click(0.03, 1.0), click(0.02, 0.5)]), 0.6))
    tt = t(0.7)
    slide = lp(noise(len(tt)), 0.08) * env(len(tt), 0.05, 0.2) * 3
    save(out, "drawer", norm(slide + np.concatenate([np.zeros(len(tt) - int(0.2 * SR)), thump(0.2, 100, 60, 0.3)]), 0.6))
    save(out, "safe_open", norm(np.concatenate([click(0.08, 1.0), tone(150, 0.9, r=0.6, harm=(1, 0.5, 0.3)) * 0.4]), 0.7))
    save(out, "punch", norm(thump(0.3, 160, 50, 1.2, 0.15), 0.9))
    # heartbeat (loop): lub-dub at 100 bpm
    beat = np.zeros(int(0.6 * SR))
    for s, a in ((0.0, 1.0), (0.16, 0.7)):
        x = thump(0.16, 70, 40, 0.1) * a
        i = int(s * SR)
        beat[i:i + len(x)] += x
    save(out, "heartbeat", norm(np.tile(beat, 14), 0.8))
    # night (loop): dark wind bed with a few crickets
    n = 30 * SR
    bed = lp_fast(noise(n), 0.01) * 6
    tt = np.arange(n) / SR
    cr = np.zeros(n)
    for c0 in np.arange(0, 30, 0.9):
        if rng.random() < 0.6:
            s = int(c0 * SR)
            ch = np.sin(2 * np.pi * 4500 * t(0.12)) * (np.sin(2 * np.pi * 40 * t(0.12)) > 0) * env(int(0.12 * SR), 0.01, 0.05) * 0.06
            cr[s:s + len(ch)] += ch[: n - s]
    save(out, "night", norm(bed * 0.6 + cr, 0.35))
    save(out, "rain", norm(lp_fast(noise(n), 0.25) * 0.8 + lp_fast(noise(n), 0.03) * 3, 0.3))
    tick = np.zeros(SR)
    tick[:len(click(0.02, 0.5))] += click(0.02, 0.5)
    save(out, "clock", norm(np.tile(tick, 8), 0.3))
    # music beds: slow dissonant drone (game), pulsing tension (chase), darker drone (menu)
    n = 60 * SR
    tt = np.arange(n) / SR
    drone = np.zeros(n)
    for f, w in ((55.0, 1.0), (82.4, 0.5), (58.3, 0.45), (110.0, 0.25), (116.5, 0.18)):
        drone += w * np.sin(2 * np.pi * f * tt + 2 * np.sin(2 * np.pi * 0.05 * tt * (1 + w)))
    drone *= 0.6 + 0.4 * np.sin(2 * np.pi * tt / 20.0) ** 2
    drone += lp_fast(noise(n), 0.004) * 4
    save(out, "game_music", norm(drone, 0.45))
    save(out, "menu_music", norm(drone * (0.7 + 0.3 * np.sin(2 * np.pi * tt / 13.0)), 0.4))
    n = 32 * SR
    tt = np.arange(n) / SR
    bpm = 132
    beat = 60.0 / bpm
    pulse = np.zeros(n)
    k = 0
    for s in np.arange(0, 32, beat / 2):
        x = thump(0.18, 120 if k % 2 == 0 else 90, 45, 0.25) * (1.0 if k % 2 == 0 else 0.55)
        i = int(s * SR)
        pulse[i:i + len(x)] += x[: n - i]
        k += 1
    bass = np.sin(2 * np.pi * 41.2 * tt) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * tt / beat))) * 0.4
    string = sum(np.sin(2 * np.pi * f * tt) for f in (220.0, 233.1, 329.6)) * 0.08 * (0.5 + 0.5 * np.sin(2 * np.pi * tt / 4.0))
    save(out, "chase_music", norm(pulse + bass + string, 0.7))
    tt = t(1.6)
    st = sum(np.sin(2 * np.pi * f * tt) for f in (196.0, 207.7, 277.2, 293.7)) * np.clip(tt / 0.25, 0, 1) * np.exp(-tt * 1.5)
    st[: int(0.3 * SR)] += thump(0.3, 150, 40, 1.0)
    save(out, "spotted", norm(st, 0.8))
    tt = t(1.4)
    js = noise(len(tt)) * np.exp(-tt * 3) * 0.8 + sum(np.sin(2 * np.pi * f * tt) for f in (155.6, 164.8, 233.1)) * np.exp(-tt * 2) * 0.5
    js[: int(0.3 * SR)] += thump(0.3, 180, 40, 1.5)
    save(out, "jumpscare", norm(js, 0.95))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sounds_synth"
    ui(os.path.join(out, "ui"))
    stand_ins(os.path.join(out, "stand_in"))
    print("done", out)
