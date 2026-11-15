"""Fetches the trailer's extra sound effects (real recordings from Freesound, via Openverse) next to the game's own pack.

    python3 tools/trailer/trailer_sounds.py OUT_DIR       -> OUT_DIR/sounds/<name>.ogg, CREDITS_TRAILER_SOUNDS.md

Uses the game's fetcher (tools/fetch_assets.py): CC0 / CC BY / CC BY-SA only, and only Freesound uploads from before
2022 (sound ids under 600000), so every sound is a real recording or a person's own sound design.
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.abspath(sys.argv[1])
sys.argv = [sys.argv[0], "sounds", OUTD]
sys.path.insert(0, os.path.join(HERE, ".."))
import fetch_assets as FA  # noqa: E402

PRE2022 = 600000
NOT_AI = r"\b(ai|a\.i\.|ai[- ]generated|generated|suno|udio|neural)\b"

TRAILER_SOUNDS = {
    "t_boom":    dict(q=["cinematic boom", "deep impact boom", "trailer hit", "low boom hit"], req=["boom", "impact", "hit", "thud"],
                      ban=["gun", "shot", "firework", "cartoon", "comic", "funny", "8bit", "8-bit", "voice", "door"],
                      dur=(0.6, 30), out=6.0, gain=0.0),
    "t_braam":   dict(q=["braam", "cinematic brass hit", "horror brass", "trailer horn"], req=["braam", "brass", "horn", "hit", "boom"],
                      ban=["car", "bike", "train", "ship", "cartoon", "comic", "party", "air horn", "airhorn", "vuvuzela"],
                      dur=(1.0, 30), out=7.0, gain=0.0),
    "t_riser":   dict(q=["horror riser", "tension riser", "suspense riser", "cinematic riser"], req=["riser", "rise", "rising", "build"],
                      ban=["cartoon", "comic", "8bit", "8-bit", "voice", "song"], dur=(2.0, 40), out=8.0, gain=-2.0),
    "t_whoosh":  dict(q=["cinematic whoosh", "whoosh", "swoosh", "fast whoosh"], req=["whoosh", "swoosh", "swish"],
                      ban=["cartoon", "comic", "sword", "wind chime", "8bit"], dur=(0.3, 8), out=2.5, gain=-2.0),
    "t_stinger": dict(q=["horror stinger", "scare stinger", "horror violin", "jump scare sound"], req=["sting", "stinger", "scare", "screech", "stab", "horror"],
                      ban=["laugh", "comic", "cartoon", "funny", "voice", "song", "loop", "ambience", "ambient"],
                      dur=(0.5, 15), out=5.0, gain=0.0),
    "t_breath":  dict(q=["scared breathing", "heavy breathing", "panting", "frightened breathing"], req=["breath", "panting", "pant"],
                      ban=["dog", "cartoon", "animal", "sex", "moan", "asthma"], dur=(2.0, 90), out=8.0, gain=-3.0),
    "t_flicker": dict(q=["fluorescent light flicker", "fluorescent buzz", "light flicker", "neon flicker"], req=["flicker", "fluorescent", "neon", "buzz", "hum"],
                      ban=["music", "song", "bee", "insect"], dur=(1.0, 120), out=6.0, gain=-4.0),
    "t_wind":    dict(q=["eerie wind", "wind howling", "night wind", "wind gusts"], req=["wind"], ban=["chime", "instrument", "music", "mic"],
                      dur=(8, 900), out=24.0, loop=True, gain=-4.0),
    "t_drone":   dict(q=["dark drone", "horror drone", "ominous drone", "low drone"], req=["drone", "dark", "ominous", "horror"],
                      ban=["bee", "quadcopter", "uav", "propeller", "flying", "airplane", "aircraft", "song", "vocal"], calm=True,
                      dur=(20, 1800), out=40.0, loop=True, gain=-3.0),
    "t_reverse": dict(q=["reverse cymbal", "reverse swell", "reverse whoosh", "reverse crash"], req=["reverse", "reversed"],
                      ban=["voice", "speech", "song", "vocal"], dur=(1.0, 12), out=4.0, gain=-2.0),
}
for spec in TRAILER_SOUNDS.values():
    spec["fs_max_id"] = PRE2022
    spec["ban_re"] = NOT_AI


def main():
    sdir = os.path.join(FA.OUT, "sounds")
    os.makedirs(sdir, exist_ok=True)
    FA.SOUND_DEADLINE[0] = time.time() + 25 * 60
    tmp = tempfile.mkdtemp(prefix="trailer_snd_")
    credits = []
    for name, spec in TRAILER_SOUNDS.items():
        if os.path.exists(os.path.join(sdir, name + ".ogg")):
            FA.log("trailer sound %-10s kept" % name)
            continue
        try:
            c = FA.openverse_fetch(name, spec, tmp)
        except Exception as e:      # noqa: BLE001
            FA.log("trailer sound failed", name, e)
            c = None
        FA.log("trailer sound %-10s %s" % (name, "ok" if c else "MISSING"))
        if c:
            credits.append(c)
    with open(os.path.join(OUTD, "CREDITS_TRAILER_SOUNDS.md"), "a") as f:
        f.write("\n".join(credits) + ("\n" if credits else ""))
    with open(os.path.join(OUTD, "trailer_sounds_report.txt"), "w") as f:
        f.write("\n".join(FA.REPORT) + "\n")
    print(json.dumps({"found": sorted(n[:-4] for n in os.listdir(sdir) if n.endswith(".ogg"))}))


main()
