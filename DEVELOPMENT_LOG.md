# DEVELOPMENT LOG — Ninja: Shadow Legacy

## Environment check (start)
* Linux cloud workspace, no display, Godot not installed. Downloaded **Godot 4.5.1** + Android
  templates from GitHub releases; Java 21 + keytool available; APK signing with uber-apk-signer.
* Network: only GitHub reachable. kenney.nl, itch.io, OpenGameArt, CraftPix, Freesound, Pixabay
  blocked → CC0 packs taken from public GitHub copies (see ASSET_CREDITS.md).
* Rendering tests run under Xvfb with Mesa (software OpenGL). No physical Android device here.

## Phase 1 — Foundation
* Portrait 720×1280 (stretch `canvas_items`, aspect `expand`), GL Compatibility renderer.
* Folder structure per PRD; autoloads: Events (signal bus + input map), GameData, SaveManager,
  AudioManager, UITheme, SpriteLib, Pool, Haptics, SceneManager.
* Asset pipeline `tools/build_assets.py` (scaling, strip packing, tile atlas, effects).

## Phase 2 — Player & controls
* `Player` (CharacterBody2D) + `PlayerStateMachine` with state classes: IDLE, RUN, JUMP, FALL,
  ATTACK, SPECIAL_ATTACK, HURT, DEATH, VICTORY (+ CLIMB).
* Coyote time, jump buffer, variable jump height, glide (hold jump), double jump (unlocked after
  World 1 boss or via power-up), ladders, drop-through platforms (down + jump), stomping.
* Multitouch controls: floating joystick + Jump/Attack/Special/Ability, press animation,
  vibration, adjustable layout editor, size/opacity/sensitivity settings.
* Camera with look-ahead, smoothing, level limits, trauma shake, hit-stop.

## Phase 3 — Combat, enemies, bosses
* Data-driven weapons (Resource .tres): Katana, Dual Blades, Shuriken, Bow, Dragon Blade —
  damage, upgrade levels 1-5, unlock rules, weapon ability.
* 6 power-ups with real effects/timers/icons. Pooled projectiles.
* 17 enemy archetypes (walker, hopper, charger, flyer, chaser, jumper, chomper, leaper, ninja,
  kunai thrower, elite) with freeze / burn status.
* Reusable `Boss` class: intro, telegraphs ("!" + red flash + ground markers), 16 attack patterns,
  phase 2 at 50 % HP, defeat slow-motion + dissolve, rewards, exit unlock.

## Phase 4 — Worlds & levels
* 34 hand-designed layout chunks; each of the 24 levels has its own chunk order, world terrain,
  enemy pool, hazards, music, colour grade and particles. Checkpoints saved to disk.
* `tools/validate_levels.py` proves every level is completable (jump-graph BFS).

## Phase 5–6 — Menus, economy, audio, save
* 16 screens: splash, main menu, continue, world select, level select, characters, weapons,
  shop (6 tabs), settings, pause, HUD, level complete, game over, boss intro, victory, credits.
* Earned-currency-only shop with confirmation, insufficient-funds message, purchase effects.
* Music cross-fades, SFX pool, bus volumes. JSON save with validation, defaults, atomic write
  and backup file.

## Phase 7 — QA & export
* `tests/smoke_test.tscn` — loads every script, opens every menu, builds all 24 levels and runs
  the player through each: **PASS**.
* `tests/flow_test.tscn` — all 6 bosses (patterns, damage, phase 2, defeat, exit unlock, level
  completion), enemy kill, chest, coins, checkpoint save, pit/respawn, lives, game over,
  shop spending, save/load, corrupted-save recovery: **PASS**.
* `tests/touch_perf_test.tscn` — simulated multitouch (joystick + jump + attack at once): **PASS**.
* `tests/screenshot_test.tscn` — rendered screenshots of menus, worlds and bosses reviewed.
* Bugs fixed during QA: shader double-multiplied texture colour (outfits rendered black), boss
  exit unlock delayed, Fire Lord too static, title overlay too large, sky bands showing white,
  portrait camera framing (added underground rows so the ninja sits higher above the controls).
* Android export (non-Gradle), arm64-v8a + armeabi-v7a, signed v2/v3 with the MXYAN release key.

## Known limitations (honest status)
* Not yet tested on a physical phone; performance was measured only on desktop hardware, so
  60 FPS is **not** claimed. Settings → Graphics quality (Low/Medium/High) and an FPS counter
  are included for on-device tuning.
* Language selection is architecture only (English).
* Asset gaps listed in ASSET_CREDITS.md (palette-variant characters/bosses, bow animation).
