# MOULIKA - The Indian Horror Game (Unity 6)

MXYAN GAMES OFFICIAL. The Unity 6 version of the Godot game on the `ragini` branch: escape Moulika ma'am's
school in three days. Same school map (built and light-baked in Blender), same Moulika (Hyper3D Rodin model with
Rodin's animations), same recorded sounds, fonts and Granny-style touch controls, drawn at the phone's full
screen resolution with 4x anti-aliasing.

## How it is built

`.github/workflows/moulika-unity.yml` runs on every push to this branch:

1. takes the game's files from the `ragini-ci` release (`school_model.zip`, `moulika_rigged.glb`,
   `sounds_pack.zip`, `assets_downloaded.zip`) and the fonts / interface images from the `ragini` branch;
2. `tools/unity/convert_assets.py` turns them into Unity data (glTF is right-handed, Unity left-handed:
   everything is mirrored on Z);
3. Unity 6000.0 (batch mode) runs `Moulika.EditorTools.MoulikaBuild.BuildAndroid`, which builds the school and
   Moulika prefabs (`Assets/Editor/SchoolBuilder.cs`, `MoulikaBuilder.cs`), the scene and the APK;
4. the APK is published as the release `moulika-unity-v<n>`; an emulator build plays through the game and its
   screenshots are attached to the same release.

## Code

| Godot (ragini branch)      | Unity (this branch)                 |
|----------------------------|-------------------------------------|
| `game/scripts/main.gd`     | `Assets/Scripts/Game.cs`            |
| `game/scripts/level.gd`    | `Assets/Scripts/Level.cs`           |
| `game/scripts/player.gd`   | `Assets/Scripts/Player.cs`          |
| `game/scripts/hud.gd`      | `Assets/Scripts/Hud.cs`, `Ui.cs`    |
| `game/scripts/ragini.gd`   | `Assets/Scripts/Enemy.cs`           |
| `game/scripts/audio.gd`    | `Assets/Scripts/GameAudio.cs`       |
| `game/scripts/mats.gd`     | `Assets/Shaders/School.shader`      |
