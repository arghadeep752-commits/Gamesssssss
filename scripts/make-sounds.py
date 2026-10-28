"""
Generates Arrow Flow's original sound effects and music loop from scratch
(pure synthesis, no samples), so every audio asset is original and tiny.

    python3 scripts/make-sounds.py      # needs numpy; ffmpeg for the music loop

Writes 22.05 kHz mono 16-bit WAV effects and an AAC (.m4a) music loop to
assets/sounds/.
"""
import os
import shutil
import subprocess
import wave

import numpy as np

SR = 22050
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds")
rng = np.random.default_rng(7)


def t(seconds):
    return np.arange(int(SR * seconds)) / SR


def env(n, attack=0.005, decay=8.0):
    """Fast attack, exponential decay envelope of n samples."""
    x = np.arange(n) / SR
    a = np.clip(x / max(attack, 1e-4), 0, 1)
    return a * np.exp(-decay * x)


def tone(freq, seconds, decay=8.0, attack=0.004, harmonics=((1, 1.0),)):
    x = t(seconds)
    s = np.zeros_like(x)
    for mult, amp in harmonics:
        s += amp * np.sin(2 * np.pi * freq * mult * x)
    return s * env(len(x), attack, decay)


def bell(freq, seconds, decay=4.0):
    return tone(freq, seconds, decay, 0.003, ((1, 1.0), (2.01, 0.35), (3.02, 0.12), (4.2, 0.05)))


def lowpass(x, alpha):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def place(total, parts):
    """Mix (offset_seconds, signal) pairs into one buffer."""
    out = np.zeros(int(SR * total))
    for offset, sig in parts:
        i = int(SR * offset)
        n = min(len(sig), len(out) - i)
        out[i : i + n] += sig[:n]
    return out


def save(name, signal, peak=0.8):
    signal = signal / (np.max(np.abs(signal)) + 1e-9) * peak
    # 4 ms fade-out to avoid clicks.
    fade = min(len(signal), int(0.004 * SR))
    signal[-fade:] *= np.linspace(1, 0, fade)
    data = (signal * 32767).astype(np.int16)
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{name:18s} {os.path.getsize(path):>7d} bytes")


def make_effects():
    # Button tap: soft, short wooden click.
    tap = tone(1250, 0.05, decay=90, harmonics=((1, 1.0), (2.4, 0.3))) + 0.15 * lowpass(rng.standard_normal(int(0.05 * SR)), 0.35) * env(int(0.05 * SR), 0.001, 120)
    save("tap.wav", tap, 0.45)

    # Arrow glide: airy noise swoosh with a rising tone underneath.
    n = int(0.22 * SR)
    x = np.arange(n) / SR
    noise = lowpass(rng.standard_normal(n), 0.25)
    swell = np.sin(np.pi * np.clip(x / 0.22, 0, 1)) ** 1.5
    freq = 420 + 520 * (x / 0.22) ** 1.4
    glide = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.35
    save("move.wav", (noise * 0.9 + glide) * swell, 0.55)

    # Blocked: muted low bump.
    bump = tone(150, 0.18, decay=22, attack=0.002, harmonics=((1, 1.0), (1.5, 0.4), (2.1, 0.15)))
    knock = lowpass(rng.standard_normal(int(0.04 * SR)), 0.2) * env(int(0.04 * SR), 0.001, 90)
    save("blocked.wav", place(0.2, [(0, bump), (0, knock * 0.6)]), 0.7)

    # Level complete: rising bell arpeggio (C5 E5 G5 C6).
    notes = [523.25, 659.25, 783.99, 1046.5]
    parts = [(i * 0.11, bell(f, 1.0, decay=3.2) * (0.8 if i < 3 else 1.0)) for i, f in enumerate(notes)]
    save("complete.wav", place(1.35, parts), 0.75)

    # Reward: two quick sparkles (E6, B6).
    save("reward.wav", place(0.55, [(0, bell(1318.5, 0.45, 7)), (0.09, bell(1975.5, 0.45, 7))]), 0.6)

    # Achievement: short fanfare (G5 C6 E6 together, then G6).
    chord = bell(783.99, 0.7, 4) + bell(1046.5, 0.7, 4) + bell(1318.5, 0.7, 4)
    save("achievement.wav", place(0.95, [(0, chord * 0.6), (0.16, bell(1567.98, 0.75, 4))]), 0.65)


def make_music():
    """A calm 16-second pad loop. Every chord fades fully in and out, so the
    loop point is silent and seamless even with encoder padding."""
    chords = [
        (261.63, 329.63, 392.00, 493.88),  # Cmaj7
        (220.00, 261.63, 329.63, 392.00),  # Am7
        (174.61, 220.00, 261.63, 329.63),  # Fmaj7
        (196.00, 246.94, 293.66, 392.00),  # G6-ish
    ]
    seg = 4.0
    total = seg * len(chords)
    out = np.zeros(int(SR * total))
    x = t(seg)
    shape = np.sin(np.pi * x / seg) ** 2  # silent at both ends of each chord
    for i, chord in enumerate(chords):
        pad = np.zeros_like(x)
        for j, f in enumerate(chord):
            detune = 1 + 0.0015 * (j - 1.5)
            pad += np.sin(2 * np.pi * f * detune * x + j) * (0.9 - 0.12 * j)
            pad += 0.25 * np.sin(2 * np.pi * f * 2 * x + j * 0.7)
        # Soft bass note.
        pad += 0.6 * np.sin(2 * np.pi * chord[0] / 2 * x)
        start = int(SR * i * seg)
        out[start : start + len(x)] += pad * shape
    # Gentle lowpass for warmth.
    out = lowpass(out, 0.18)
    wav = os.path.join(OUT, "_music.wav")
    tmp = out / (np.max(np.abs(out)) + 1e-9) * 0.6
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((tmp * 32767).astype(np.int16).tobytes())
    m4a = os.path.join(OUT, "music.m4a")
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to encode music.m4a")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "aac", "-b:a", "40k", "-ac", "1", m4a],
        check=True,
    )
    os.remove(wav)
    print(f"{'music.m4a':18s} {os.path.getsize(m4a):>7d} bytes")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_effects()
    make_music()
