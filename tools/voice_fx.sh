#!/bin/bash
# Chaya - the Pujari's voice-over for the opening cutscene: a recording (e.g. from ElevenLabs) made deeper and given
# the echo of a big stone hall, levelled for a phone speaker.
#   tools/voice_fx.sh <voice.mp3|wav> [assets/voice/pujari_chalisa.ogg] [pitch factor, default 0.96]
set -euo pipefail
IN="$1"
OUT="${2:-assets/voice/pujari_chalisa.ogg}"
P="${3:-0.96}"
mkdir -p "$(dirname "$OUT")"
T=$(python3 -c "print(round(1.0 / $P, 5))")
ffmpeg -hide_banner -loglevel error -y -i "$IN" -ac 1 -af "highpass=f=70,\
asetrate=44100*$P,aresample=44100,atempo=$T,\
bass=g=3:f=110,acompressor=threshold=-18dB:ratio=3:attack=10:release=220,\
aecho=0.8:0.9:55|120|240|380:0.34|0.24|0.16|0.09,\
apad=pad_dur=1.5,loudnorm=I=-14:TP=-1.5:LRA=11" -ar 44100 -c:a libvorbis -q:a 5 "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1 "$OUT"
