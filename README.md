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

## Next steps

Unity 6 project from the exported house and models, real photo textures (Poly Haven / ambientCG, CC0) on the walls,
floors and furniture, cleaned-up rooms and brighter lighting, the gameplay rebuilt, and the APK on the Releases page.

## Credits

Original game: Granny 4 End Game on Game Jolt (https://gamejolt.com/games/granny4endgame/1117042). The Granny series is
by DVloper.
