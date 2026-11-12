"""Chaya - the Pujari's Hanuman Chalisa for the opening cutscene, spoken by an ElevenLabs voice.

    python3 eleven_voice.py <api key> <out.mp3>

Picks a deep, Indian male voice from the ElevenLabs voice library (adds it to the account), falls back to a deep
premade voice, and speaks the opening dohas and first chaupais of the Hanuman Chalisa (Goswami Tulsidas, public domain).
"""
import json
import sys
import urllib.error
import urllib.request

KEY, OUT = sys.argv[1], sys.argv[2]
API = "https://api.elevenlabs.io/v1"

TEXT = """श्रीगुरु चरन सरोज रज, निज मनु मुकुरु सुधारि।
बरनउँ रघुबर बिमल जसु, जो दायकु फल चारि॥
बुद्धिहीन तनु जानिके, सुमिरौं पवन-कुमार।
बल बुधि बिद्या देहु मोहिं, हरहु कलेस बिकार॥
जय हनुमान ज्ञान गुन सागर। जय कपीस तिहुँ लोक उजागर॥
राम दूत अतुलित बल धामा। अंजनि-पुत्र पवनसुत नामा॥"""


def call(method, path, body=None, raw=False):
    req = urllib.request.Request(API + path, method=method, headers={"xi-api-key": KEY, "Content-Type": "application/json",
                                                                     "Accept": "audio/mpeg" if raw else "application/json"})
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=120) as r:
        out = r.read()
    return out if raw else json.loads(out.decode() or "{}")


def pick_voice():
    for q in ("language=hi&gender=male&age=middle_aged", "language=hi&gender=male", "accent=indian&gender=male"):
        try:
            res = call("GET", "/shared-voices?page_size=60&sort=trending&" + q)
        except urllib.error.HTTPError as e:
            print("voice library:", e.code, e.read()[:200])
            continue
        voices = res.get("voices", [])
        deep = [v for v in voices if "deep" in (str(v.get("descriptive", "")) + " " + v.get("name", "") + " " +
                                                 v.get("description", "")).lower()]
        for v in deep + voices:
            try:
                added = call("POST", "/voices/add/%s/%s" % (v["public_owner_id"], v["voice_id"]), {"new_name": "Chaya Pujari"})
                print("library voice:", v.get("name"), v.get("accent"), v.get("descriptive"), "->", added.get("voice_id"))
                return added.get("voice_id") or v["voice_id"]
            except urllib.error.HTTPError as e:
                print("could not add", v.get("name"), e.code, e.read()[:160])
                if e.code in (401, 403):
                    break
    print("falling back to a premade deep voice")
    return "nPczCjzI2devNBz1zQrb"        # Brian - deep, resonant (premade)


vid = pick_voice()
audio = call("POST", "/text-to-speech/%s?output_format=mp3_44100_128" % vid,
             {"text": TEXT, "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True,
                                 "speed": 0.9}}, raw=True)
open(OUT, "wb").write(audio)
print("voice written:", OUT, len(audio), "bytes")
