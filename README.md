# Ninja: Shadow Legacy — MXYAN GAMES

2D action platformer for Android (portrait), Godot 4.5 / GDScript.

## Play
Install `NinjaShadowLegacy-v1.0.apk` on an Android phone (Android 7+). Allow
"install unknown apps" for your browser/file manager when asked.

## Open the project
Open this folder (or import the ZIP) in **Godot 4.5.x** (desktop or the Godot Android editor).
Main scene: `scenes/splash/splash.tscn`. Keyboard on desktop: A/D move, Space jump, J attack,
L special, I ability, Esc pause.

## Structure
* `scripts/` — core (data, scenes, pooling), player (+ state machine), combat, enemies, bosses,
  levels (chunk library + builder), gameplay, ui, audio, save
* `resources/` — characters, weapons, power-ups, skins, 24 levels (.tres, editable)
* `assets/`, `fonts/`, `shaders/` — CC0 artist assets (see ASSET_CREDITS.md)
* `tests/` — headless smoke / flow / touch tests
* `tools/` — asset pipeline + level validator (Python)

## Re-building the APK
Editor → Project → Export → Android → Export Project. The preset exports unsigned; sign with your
own key, or the MXYAN key in `signing/` (keep that file and password private — the same key is
needed to install updates over the existing app).
