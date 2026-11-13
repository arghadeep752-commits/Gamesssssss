# RAGINI - The Indian Horror Game

A Granny-style 3D horror game for Android by **MXYAN GAMES OFFICIAL**.
You are locked inside a creepy old Indian school with Ragini, a chudail in a red saree with burning red eyes and a
wooden scale in her hand. Find the hammer to pull the planks off the main door and the main door key to unlock it.
You have three days.

* Engine: Godot 4 (GDScript, GL Compatibility renderer)
* Every 3D model - Ragini, the school, the furniture, the keys and the hammer - is built in **Blender** by the
  scripts in `tools/` (nothing is downloaded or AI-generated). The `.blend` files are attached to each release.
* Textures are real photographs (CC0 photo-scanned surfaces), sounds are real recordings; see CREDITS.md on the release.
* Build: GitHub Actions (`.github/workflows/ragini.yml`) runs Blender, imports into Godot and publishes the APK on the
  Releases page.
