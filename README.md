# Grid Prototype — Unity 6 first-person mobile prototype

A realistic first-person prototype for Android phones made with **Unity 6 (6000.0 LTS)**, built entirely in
the cloud with GitHub Actions — no PC needed.

No map yet: a white grid prototype landscape with blocks, stairs, pushable physics cubes and a small test
room with a door you can open.

## Get the APK

Every push to this branch builds a new APK and publishes it on the repository's **Releases** page as
`grid-prototype-build-<number>`. Open the release on your phone, download the `.apk` and tap it to install.
Emulator screenshots of each build are attached to the same release.

## The enemy

A hooded man in a wooden mask (your Red Hooded Hollow model, rigged and animated in code) hunts you:

- **Patrols** the area, stopping to look around now and then
- **Sees** you inside his view cone when nothing blocks the line of sight (harder to spot you when crouching)
- **Hears** you: running footsteps, landing from a jump and the door give you away; crouch-walking is quiet
- **Chases** at a sprint with a realistic run cycle, aiming where you are heading and pathing around blocks;
  he even opens the door if you hide in the room
- **Gets confused** when you get very far away: stops, looks left and right, scratches his head, then
  searches the last place he saw you before going back to patrolling
- **Catches** you: grabs you by the throat, lifts you up and punches you in the face three times — then
  "YOU WERE CAUGHT" and TRY AGAIN

## Controls

- **Left side**: floating joystick — touch anywhere on the left half; push all the way forward to run
- **Right side**: drag to look around
- **JUMP** and **CROUCH** buttons (bottom right), **pause** (top right: sensitivity, graphics, FPS counter)
- **OPEN / CLOSE** button pops up when you are close to the door; the door swings away from you

## What makes it look and feel real

- Renders at the phone's **full native resolution** (no scaled-down buffer) with 4x MSAA and sharp,
  high-resolution UI drawn in code
- Linear lighting, soft real-time sun shadows, sky, distance fog, reflections, soft contact shadows under
  every block and a warm ceiling light inside the room
- Seamless 4 m prototype grid texture with 1 m lines and subtle grooves (normal map), aligned to the world
- Movement with momentum, head bob, footsteps, landing dip, sprint FOV, crouch, door sounds and wind

## Project layout

- `Assets/Editor/` — build script: generates the textures, materials, meshes and the level, then builds the APK
  (in the Unity editor: menu **Grid Prototype → Rebuild Scene / Build Android APK**)
- `Assets/Scripts/` — the game: player, touch controls, HUD, door, sounds, settings
- `Assets/Shaders/` — contact shadow shader
- `.github/workflows/grid-prototype.yml` — cloud build, release and emulator test
- `ci/` — helper scripts for the cloud build

## One-time setup

The repository needs the secrets `UNITY_EMAIL` and `UNITY_PASSWORD` (a free Unity account with two-step
verification turned off) under **Settings → Secrets and variables → Actions**.
