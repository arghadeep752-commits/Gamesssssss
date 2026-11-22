# DANGA - Godot 4 version

Open-world game set in Agartala, Tripura, made with Godot 4.6 (GL Compatibility renderer, Jolt physics) for Android.
This is the port of the Unity 6 version on the `danga` branch.

## What is in this folder

- `project.godot`, `scenes/main.tscn` - the project; everything is built from code by `scripts/game.gd`
- `scripts/` - gameplay: player, people, traffic and police (`traffic.gd`, `ped.gd`, `wanted.gd`), vehicles with an
  arcade driving model (`vehicle.gd`), weapons (`combat.gd`), the city streaming (`city.gd`), day and night (`env.gd`),
  the HUD, menus, phone and map (`hud.gd`, `menus.gd`), saving (`save.gd`) and the automatic play-through (`autotest.gd`)
- `shaders/` - city materials (texture array with normal maps), terrain, trees, water, sky, street-lamp glow
- `gen/` - generated content: the city, the Hyper3D Rodin models, sounds, music, fonts and interface art. It is not in
  git; the build makes it (below). The full project zip on the GitHub release already contains it.

## Opening it

Download `Danga-Godot-full-project.zip` from a `danga-godot-v<n>` release, unzip it and open the `Danga-Godot` folder
(or import the zip) in the Godot 4.6 editor - on a PC, or the Godot editor app for Android. The first import takes a
while because of the city and the models.

## Building the generated content yourself

From the repository root, with Python 3 and numpy, pillow, matplotlib and scipy:

```
python3 tools/rodin_fetch.py dl/rodin                       # Hyper3D models (from the danga-ci release)
python3 tools/city/build.py --assets <downloaded assets> --out build/unused --godot godot/gen
python3 tools/godot/convert_models.py --rodin dl/rodin --models tools/rodin/models.json --out godot/gen/models
python3 tools/ui/make_ui.py --ui <assets>/ui --out godot/gen/ui --branding godot/gen/branding --font <assets>/fonts/DisplayFont.ttf
python3 tools/godot/prepare.py --gen godot/gen --assets <assets> --sounds <assets>/sounds --music <assets>/music
```

`.github/workflows/danga-godot.yml` does all of this in the cloud and exports the APK.

## Testing on a PC

`godot --path godot -- --dg-test` plays through the game (menus, walking, shooting, the bike, a car, the palace, the
map, the gun shop, the boat, the helicopter, night and the police) and saves screenshots to `/tmp/dgtest`.
