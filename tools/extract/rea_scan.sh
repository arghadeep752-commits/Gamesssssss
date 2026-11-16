#!/usr/bin/env bash
# Reads the names in the game's code with rea (github.com/morluto/rea): classes, methods, fields and text strings.
# IL2CPP games: rea inspect-il2cpp-metadata on global-metadata.dat. Mono games: rea inspect-managed-members.
# usage: rea_scan.sh <work dir> <out dir>
set -uo pipefail
W="$1"; OUTD="$2"
mkdir -p "$OUTD"
npm install --global --no-fund --no-audit rea-agents@latest > "$W/rea_install.log" 2>&1 \
  || { echo "rea install failed"; tail -n 30 "$W/rea_install.log"; exit 1; }
rea --version 2>/dev/null | head -n 2 || true

DATA="$W/apk/assets/bin/Data"
META="$DATA/Managed/Metadata/global-metadata.dat"
if [ -f "$META" ]; then
  echo "IL2CPP metadata: $(du -h "$META" | cut -f1)"
  timeout 1500 rea inspect-il2cpp-metadata "$(realpath "$META")" --json > "$W/rea_il2cpp.json" 2> "$W/rea_il2cpp.err"
  echo "rea exit $? ; output $(du -h "$W/rea_il2cpp.json" | cut -f1)"
  head -c 1500 "$W/rea_il2cpp.err"; echo
  python3 tools/extract/rea_summary.py il2cpp "$W/rea_il2cpp.json" "$OUTD"
fi
DLL="$DATA/Managed/Assembly-CSharp.dll"
if [ -f "$DLL" ]; then
  echo "Mono assembly: $(du -h "$DLL" | cut -f1)"
  timeout 1500 rea inspect-managed-members "$(realpath "$DLL")" --json > "$W/rea_managed.json" 2> "$W/rea_managed.err"
  echo "rea exit $? ; output $(du -h "$W/rea_managed.json" | cut -f1)"
  head -c 1500 "$W/rea_managed.err"; echo
  python3 tools/extract/rea_summary.py managed "$W/rea_managed.json" "$OUTD"
fi
