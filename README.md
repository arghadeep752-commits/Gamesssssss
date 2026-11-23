# Soul Eater Test

A first-person horror prototype in Godot 4.6: one room with a locked door, an old sofa and a chest
of drawers whose drawers open.

## Controls (phone)
- **Joystick** (bottom left): walk
- **Drag anywhere else**: look around
- **Pointer** (small circle in the middle): aim it at the door - its name shows under it
- **USE** (right): appears while you aim at the door or a drawer; the door rattles (it's locked),
  drawers slide open and shut

On a computer: WASD or arrows, drag the mouse to look, E to use.

## Project
- `main.tscn` - the room, lights and environment
- `scenes/player.tscn`, `scenes/door.tscn`, `scenes/hud.tscn` - player, door, on-screen controls
- `scripts/` - the GDScript code (`dresser.gd` / `drawer.gd` make the drawers open)
- `assets/models/` - the Sketchfab sofa and chest of drawers
- `assets/` - textures, materials, font, sounds, UI images
- `tools/` - scripts that made the textures, UI images and room reflection (not part of the game)

Lighting: Godot's sun + WorldEnvironment with Filmic tone mapping, glow and a light colour grade,
a hanging lamp, and PBR materials. The environment's sky is a 360 degree picture of the room
itself, so the floor, door and brass knob reflect the room.

## Building the APK
Push to the `locked-room` branch: `.github/workflows/locked-room.yml` downloads Godot, exports the
APK and puts it on the Releases page. The APK is signed with the test key in
`tools/locked-room-test.keystore` (fine for testing; make your own private key before a store release).

Credits: see CREDITS.md.
