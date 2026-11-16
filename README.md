# Granny Dimnight (Unity 6)

A Unity 6 remake of **Granny 4 End Game** (Game Jolt, game 1117042), shared with the original creator's agreement:
the same house, layout, 3D models and gameplay, made clean and bright with real photo textures, renamed
**Granny Dimnight** and built into an Android APK in the cloud, with no PC needed.

## Step 1: look inside the original (`.github/workflows/granny-dimnight-extract.yml`)

Every push that changes `tools/extract/` runs:

1. `tools/extract/gamejolt_fetch.py`: downloads the Android build from Game Jolt the way the website does
   (`/site-api/web/discover/games/packages/<id>` then `/builds/get-download-url/<build>`);
2. `tools/extract/inspect_apk.sh`: package, name, version, Unity version, IL2CPP or Mono;
3. `tools/extract/rea_scan.sh`: [rea](https://github.com/morluto/rea) reads the class, method and field names and the
   text strings in the game's code (`rea inspect-il2cpp-metadata` / `rea inspect-managed-members`);
4. `tools/extract/assetripper_export.sh`: [AssetRipper](https://github.com/AssetRipper/AssetRipper) exports the
   scenes, models, materials, textures, sounds and scripts (as a Unity project, and every scene as `.glb`);
5. `tools/extract/report.py`: writes `original/report.md`, every scene's objects with their world positions
   (`original/scenes/*.json`), the materials, texture contact sheets and the game's scripts;
6. `tools/extract/render_house.py` (Blender 4.2): floor plans and eye-height views of the house in `original/renders/`.

Only these findings are committed (in `original/`); the game's files are not re-uploaded anywhere.

## Step 2: the Unity 6 APK (`.github/workflows/granny-dimnight.yml`)

Every push that changes `Unity/`, `tools/unity/` or `ci/` runs:

1. the Game Jolt download and AssetRipper export again (the game's files are never stored in this repository);
2. `tools/unity/prepare_project.py`: the exported scenes, models, materials, menus, sounds and animations go into the
   Unity project in `Unity/`; the rewritten game scripts in `Unity/Overrides/Assembly-CSharp/` replace AssetRipper's
   empty stubs (same class names, same settings, same `.meta`, so the scenes stay connected);
3. `tools/unity/real_textures.py`: walls, floors, stairs, tiles, wood panels, stone and grass become photo-scanned
   CC0 textures (Poly Haven, ambientCG), tinted to each room's original colour; furniture and props keep theirs;
4. `tools/unity/branding.py`: the GRANNY DIMNIGHT menu picture (replacing DVloper's artwork) and the app icon;
5. Unity 6000.0 downloads the packages, then `tools/unity/remap_packages.py` points every reference to AssetRipper's
   stand-in DLLs and dummy shaders at the real UGUI / TextMeshPro / URP / AI Navigation / Timeline files
   (class ids from `original/dll_classes.json`, computed with `tools/common/unity_ids.py`);
6. `Dimnight.EditorTools.DimnightBuild.BuildAndroid` (`Unity/Assets/Dimnight/Editor/`): Granny Dimnight name and
   package `com.anomynousdevs.grannydimnight`, URP materials, renamed texts, no blood, Granny's navmesh baked again
   (the export has none), URP 17 post-processing resources, IL2CPP ARM64 APK;
7. the APK is published as the release `granny-dimnight-v<n>`; an emulator build plays the start of the game (menu,
   Day 1, waking up, a walk through every room, a look at Granny) and its screenshots are attached to the same release.

## The game scripts (`Unity/Overrides/Assembly-CSharp/`)

The original's code is IL2CPP, so only its class, field and method names survive. Every gameplay script is written
again from those names, the scene settings and the game's text strings: the player and touch controls, the hand
button (pick up, use, drop), doors, drawers, keys and planks, hiding (beds, coffin, cabinet, car), Granny's patrol,
hearing, sight, chase and the kill and bed/coffin/car jumpscares, the five days, the main-door locks (plank, code
padlock, padlock, chain, secret bookshelf) and the master key ending, the hot air balloon escape (duct tape, gas
cylinder, lighter, cutting the anchor ropes), Extreme mode's lever and fence, creaking floors, the doorbell tripwire,
falling paintings and crashing furniture, settings, music and the endings. There are no ads.

## Credits

Original game: Granny 4 End Game on Game Jolt (https://gamejolt.com/games/granny4endgame/1117042). The Granny series is
by DVloper.
