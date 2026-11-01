# Silent Valley — realistic first-person Unity prototype (Android)

A first-person exploration prototype for Android phones, made with **Unity 6 (6000.0 LTS)** and the
**Universal Render Pipeline (URP)**, built entirely in the cloud with GitHub Actions — no PC needed.

You walk through a mountain valley with a lake, a fir forest, a pier and a campfire, and look for 5 lost
lanterns.

## Get the APK

Every push to this branch builds a new APK and publishes it on the repository's **Releases** page as
`realistic-fps-build-<number>`. Open it on your Android phone and tap the `.apk` file to install.
The emulator screenshots of each build are attached to the same release.

## Controls

- **Left side of the screen**: floating joystick — push it all the way forward to sprint
- **Right side**: drag to look around
- **Jump** (big button), **crouch**, **run lock**, **pause** (top-right)
- **Pick up** appears next to a lantern

## Graphics

- Real HDRI sky (Poly Haven `kloofendal_48d_partly_cloudy_puresky`) for the skybox, the ambient light
  (spherical harmonics) and reflections; the sun matches the sky.
- Photo-scanned PBR textures for the terrain (grass, forest floor, lichen rock, lake-shore pebbles) and
  photo-scanned models (rock faces, mossy boulders, ferns, wooden pier, fire pit, oil lanterns).
- Procedural fir trees using Poly Haven's fir-branch texture atlas, with three levels of detail, drawn
  with GPU instancing (a few dozen draw calls for the whole forest).
- URP terrain (4 PBR layers with normal maps) with wind-blown terrain grass, a lake shader with sky
  reflections, sun glints and shore depth, distant mountain range, fog, linear lighting, URP shadows and a
  post-processing volume (ACES tonemapping, colour grading, white balance, subtle vignette, restrained
  bloom on High). No depth of field or motion blur.
- Three graphics profiles, picked automatically from the phone's GPU and memory and changeable in
  Settings (each is a URP asset + quality level, see `Assets/Editor/RFRenderSetup.cs`):

  | | Low | Medium | High |
  |---|---|---|---|
  | Render resolution (short side, max) | 720 px | 900 px | 1080 px |
  | MSAA | 2x | 2x | 4x |
  | Sun shadows | 25 m, 1024, hard | 38 m, 1024, soft | 60 m, 2048, 2 cascades, soft |
  | Grass distance / density | 16 m / 35% | 28 m / 65% | 42 m / 100% |
  | Tree detail distance | x0.7 | x1.0 | x1.35 |
  | Bloom / vignette | off / off | off / on | on / on |

- Settings: graphics profile, 30 or 60 FPS, look sensitivity, field of view, invert look, head bob, FPS
  counter. The render resolution drops a little at a time when the frame rate cannot keep up.

## One-time setup

Unity needs a (free) Unity Personal license to build. Add two repository secrets under
**Settings → Secrets and variables → Actions**: `UNITY_EMAIL` and `UNITY_PASSWORD`
(two-step verification must be off on that Unity account).

## Project layout

- `tools/fetch_assets.py` — downloads the CC0 assets from Poly Haven (in CI)
- `tools/process_assets.py` — turns them into game textures, atlases, sky data; generates sounds and UI icons
- `Assets/Editor/` — the build script: creates the terrain, sky, lake, forest, props and the scene, then builds the APK
- `Assets/Scripts/` — the game (player controller, touch controls, menus, quality settings, grass, post-processing)
- `Assets/Shaders/` — water, foliage, grass, distant mountains and post-processing shaders
- `.github/workflows/realistic-fps.yml` — the cloud build and emulator test

## Credits

Sky, textures and 3D models: [Poly Haven](https://polyhaven.com) (CC0). Fonts: Barlow and Cinzel (SIL Open Font License).
