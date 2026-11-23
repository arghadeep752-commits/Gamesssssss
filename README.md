# Locked Room

A first-person horror prototype in Godot 4.6: one room with a locked door, nothing else.

## Controls (phone)
- **Joystick** (bottom left): walk
- **Drag anywhere else**: look around
- **Figure button** (left): crouch / stand
- **Pause** (top left): pause menu with **look sensitivity** (- / slider / +)
- **Hand + USE** (right): appears when you look at the door; the door rattles - it's locked
- Android back button opens the pause menu

On a computer: WASD or arrows, drag the mouse to look, C crouch, E use, Esc pause.

## Project
- `main.tscn` - the room, lights and environment
- `scenes/player.tscn`, `scenes/door.tscn`, `scenes/hud.tscn` - player, door, on-screen controls
- `scripts/` - the GDScript code
- `assets/` - textures, materials, font, sounds, UI images
- `tools/` - scripts that made the textures, UI images and room reflection (not part of the game)

Lighting: Godot's sun + WorldEnvironment with Filmic tone mapping, glow and a light colour grade,
a hanging lamp, and PBR materials. The environment's sky is a 360 degree picture of the room
itself, so the floor, door and brass knob reflect the room.

## Building the APK
Push this project to the `locked-room` branch: `.github/workflows/locked-room.yml` downloads Godot,
exports the APK and puts it on the Releases page. The APK is signed with the test key in
`tools/locked-room-test.keystore` (fine for testing; make your own private key before a store release).

Credits: see CREDITS.md.
