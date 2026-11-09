"""Real recordings for the trailer soundtrack, from Wikimedia Commons (no synthesis, no AI).

    python3 tools/trailer/fetch_sfx.py <out dir>

Uses the game's Commons search / processing (tools/fetch_assets.py). Licences without ShareAlike (CC0, public domain,
CC BY) are tried first; CC BY-SA only when nothing else is found. Writes <out>/<name>.ogg, report.txt, credits.txt.
"""
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fetch_assets as fa  # noqa: E402

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "build/trailer_snd")
os.makedirs(OUT, exist_ok=True)
fa.OUT_SND = OUT
NO_SA = re.compile(r"^(cc0|cc[- ]zero|public domain|pd|cc[- ]by(?![- ]nc)(?![- ]sa)|attribution(?!.*share))", re.I)
ANY = fa.OK_LICENSE

SPECS = {
    "boom":      dict(q=["bass drum hit", "bass drum", "taiko drum", "timpani hit", "big drum hit", "kick drum", "timpani"],
                      req=["bass drum", "taiko", "timpani", "kick", "big drum", "drum hit", "boom"],
                      ban=["roll", "loop", "beat", "rhythm", "song", "music", "kit", "groove", "pattern", "solo", "march", "band"], dur=(0.3, 40), out=4.0),
    "dhol":      dict(q=["dhol", "nagara drum", "nagada", "dhak drum", "Indian drum", "dholak", "mridangam", "tabla"],
                      req=["dhol", "nagara", "nagada", "dhak", "dholak", "mridang", "tabla", "pakhawaj", "drum"],
                      ban=["song", "remix", "kit", "bhangra", "dance"], dur=(2, 600), out=14.0, raw=True),
    "conch":     dict(q=["conch shell blowing", "shankha", "shankh", "conch shell", "conch", "blowing conch", "shell trumpet"],
                      req=["conch", "shankh", "shankha", "sankha", "shell trumpet", "sangu"], ban=["song"], dur=(1, 200), out=7.0),
    "ghungroo":  dict(q=["ghungroo", "ankle bells", "anklet bells", "dancer ankle bells", "jingle bells shaking", "small bells jingle", "sleigh bells"],
                      req=["ghung", "ankle", "anklet", "payal", "jingl", "sleigh bell", "small bell"], ban=["song", "christmas song", "music"], dur=(0.5, 200), out=6.0),
    "cymbal":    dict(q=["cymbal crash", "crash cymbal", "cymbal", "suspended cymbal", "gong hit", "gong"],
                      req=["cymbal", "crash", "gong"], ban=["car", "accident", "glass", "song", "music", "loop", "beat"], dur=(1, 60), out=6.0),
    "tanpura":   dict(q=["tanpura", "tambura", "tanpura drone", "tanpoora", "shruti box", "harmonium drone"],
                      req=["tanpura", "tambura", "tanpoora", "tanboura", "shruti", "drone"], ban=["song", "remix"], dur=(8, 1500), out=40, loop=True),
    "whoosh":    dict(q=["whoosh", "swoosh", "swish", "whoosh sound effect", "air swish"], req=["whoosh", "swoosh", "swish", "woosh"],
                      ban=["song", "music", "lead", "synth", "rave", "electronic", "laser", "sci-fi", "game"], dur=(0.2, 30), out=2.5),
    "thunder":   dict(q=["thunder", "thunderclap", "thunder rumble", "thunderstorm", "distant thunder"], req=["thunder"],
                      ban=["song", "music", "band"], dur=(2, 300), out=10.0),
    "wind":      dict(q=["wind howling", "strong wind", "wind blowing", "winter wind", "wind noise", "wind"], req=["wind"],
                      ban=["song", "music", "instrument", "chime", "turbine", "orchestra"], dur=(6, 900), out=30, loop=True),
    "buzz":      dict(q=["electric buzz", "fluorescent light buzz", "electrical hum", "transformer hum", "neon hum", "power line hum", "mains hum"],
                      req=["buzz", "hum", "electric", "fluorescent", "transformer", "neon"], ban=["song", "music", "bee", "insect", "fly", "mosquito", "humming bird", "voice", "sing"],
                      dur=(1, 600), out=6.0),
    "blowout":   dict(q=["blowing out candle", "blow out candle", "candle blow", "blowing air", "breath out", "exhale"],
                      req=["blow", "candle", "breath", "exhal", "puff"], ban=["song", "music", "glass", "horn", "whistle", "trumpet"], dur=(0.3, 40), out=2.0),
    "chant":     dict(q=["Om chanting", "Om mantra", "Hindu chant", "mantra chanting", "Vedic chanting", "Sanskrit chant", "chanting"],
                      req=["om ", "om_", "chant", "mantra", "vedic", "sanskrit", "sloka", "shloka", "stotra"], ban=["gregorian", "christian", "remix"],
                      dur=(8, 1500), out=30, loop=True),
    "heartbeat": dict(q=["heartbeat", "heart beat", "heartbeat sound", "heart sounds", "fetal heartbeat"], req=["heart"],
                      ban=["song", "music", "act", "law", "ecg", "monitor", "bill"], dur=(4, 300), out=12, loop=True),
    "scream":    dict(q=["woman screaming", "female scream", "horror scream", "scream", "shriek"], req=["scream", "shriek"],
                      ban=["song", "music", "baby", "child", "kid", " male", "boy", "radio"], dur=(0.6, 60), out=3.0),
    "breath":    dict(q=["heavy breathing", "breathing", "woman breathing", "breath"], req=["breath"], ban=["song", "music", "exercise", "running"],
                      dur=(1, 300), out=6.0),
}


def main():
    tmp = tempfile.mkdtemp(prefix="trailer_snd_")
    # the licence filter is a module global in fetch_assets: strict pass for everything (in parallel), then a relaxed
    # pass only for the sounds the strict pass could not find
    fa.OK_LICENSE = NO_SA
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = dict(zip(SPECS, ex.map(lambda kv: fa.fetch_sound(kv[0], kv[1], tmp), SPECS.items())))
    miss = [k for k, (_, c) in res.items() if c is None]
    fa.OK_LICENSE = ANY
    if miss:
        with ThreadPoolExecutor(max_workers=6) as ex:
            res.update(dict(zip(miss, ex.map(lambda k: fa.fetch_sound(k, SPECS[k], tmp), miss))))
    report = [res[k][0] for k in SPECS]
    report.append("")
    report += ["%-22s rms %6.1f dBFS  peak %5.1f dBFS  %5.1fs" % (k, *v) for k, v in sorted(fa.LEVELS.items())]
    open(os.path.join(OUT, "report.txt"), "w").write("\n".join(report) + "\n")
    clean = [re.sub(r"\s*8=+D", "", c) for _, c in res.values() if c]
    open(os.path.join(OUT, "credits.txt"), "w").write("\n".join(clean) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
