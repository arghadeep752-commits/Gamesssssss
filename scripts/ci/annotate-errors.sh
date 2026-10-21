#!/usr/bin/env bash
# Turns the useful part of a failed build log into GitHub error annotations
# (visible on the run page and through the API, even when raw logs aren't):
# Gradle "What went wrong" blocks, Kotlin/Java/AAPT errors, and the log's tail.
#
#   annotate-errors.sh <log-file> <title>
LOG="${1:?log}"
TITLE="${2:-Build}"
[ -s "$LOG" ] || { echo "no log at $LOG"; exit 0; }
python3 - "$LOG" "$TITLE" <<'PY'
import re
import sys

path, title = sys.argv[1], sys.argv[2]
lines = [l.rstrip("\r") for l in open(path, errors="replace").read().splitlines()]
ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
lines = [ansi.sub("", l) for l in lines]
# Stack frames add nothing an error message doesn't already say.
lines = [l for l in lines if not re.match(r"^\s+at |^\s+\.\.\. \d+ more", l)]

sections = []

# 1. Gradle's own summary ("* What went wrong:" up to "* Try:")
blocks, cur = [], None
for l in lines:
    if l.startswith("* What went wrong"):
        cur = [l]
    elif cur is not None:
        if l.startswith("* Try") or l.startswith("* Exception is") or l.startswith("* Get more help"):
            blocks.append("\n".join(cur)); cur = None
        else:
            cur.append(l)
if cur:
    blocks.append("\n".join(cur))
if blocks:
    sections.append(("What went wrong", "\n\n".join(blocks)))

# 2. Compiler / tool errors with a little context
pat = re.compile(r"(^e: |^error:|: error:|\berror TS\d+|ERROR:|Unresolved reference|Missing class|AAPT: error|Could not (find|resolve|get)|npm (ERR|error)|\bFAILED\b|Exception in thread|Caused by:)")
keep = []
for i, l in enumerate(lines):
    if pat.search(l):
        keep.extend(range(max(0, i - 1), min(len(lines), i + 3)))
seen, picked = set(), []
for j in keep:
    if j not in seen:
        seen.add(j); picked.append(lines[j])
if picked:
    sections.append(("Errors", "\n".join(picked[:400])))

# 3. The end of the log
sections.append(("Log tail", "\n".join(lines[-80:])))

def esc(s):
    return s.replace("%", "%25").replace("\r", "").replace("\n", "%0A")

count = 0
for name, body in sections:
    for k in range(0, len(body), 12000):
        if count >= 9:
            break
        print(f"::error title={title} - {name}::{esc(body[k:k + 12000])}")
        count += 1
PY
