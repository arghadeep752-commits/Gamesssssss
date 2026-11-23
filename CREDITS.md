# Soul Eater Test - credits and licences

Every sound is a real recording and every picture was made by a person. Nothing here is AI generated.

## Textures
- **Door, wallpaper and parquet floor**: the three photos supplied by the developer
  (`tools/source_images`). The wallpaper's colour is turned from lime to green; the normal and
  roughness maps are worked out from the photos themselves (`tools/make_textures.py`); the floor
  photo was cut to an exact repeat so it tiles.
- **Room reflection** (`assets/textures/room_reflection.png`): a 360 degree capture of this room,
  made by `tools/bake_room_reflection.gd`.

## 3D models (from Sketchfab, CC BY 4.0 - credit required)
- **Sofa**: "Old Couch" (https://sketchfab.com/3d-models/old-couch-8da7e0d122f544e2862b4e592988e183)
  by Oliver Triplett (https://sketchfab.com/OliverTriplett), licensed under CC-BY-4.0
  (http://creativecommons.org/licenses/by/4.0/). Textures scaled down to 1024 px.
- **Chest of drawers**: "Dresser" (https://sketchfab.com/3d-models/dresser-1a0cb6ce3e1d4e27b7f684f4d4e946c1)
  by Ally Furnish (https://sketchfab.com/furnisha), licensed under CC-BY-4.0
  (http://creativecommons.org/licenses/by/4.0/). The drawers were made to slide open in the game.
- Each model folder keeps its original `license.txt`.

## Font
- **Chalk-y** by Ştefancu Gabi, from dafont: https://www.dafont.com/chalk-y.font
  (listed as "100% Free").

## Sounds
- **Footsteps** (`footstep_01` to `footstep_04`): `Footstep01.wav` to `Footstep04.wav` from Unity's
  Standard Assets (FirstPersonCharacter), Unity Technologies, Unity Asset Store EULA.
- **Locked door rattles**: recordings from Freesound, all CC0 (public domain), cut and levelled:
  - `door_rattle_1`, `door_rattle_2`: "Cottage Door Handles - Assorted Opening, Rattling and Closing"
    by EpicWizard - https://freesound.org/people/EpicWizard/sounds/345312/
  - `door_rattle_3`: "Door rattles, wood, 2011" by TRP - https://freesound.org/people/TRP/sounds/577273/
  - `door_rattle_4`: "Door Handle Rattling" by MarcusGraham325 - https://freesound.org/people/MarcusGraham325/sounds/330829/

- **Drawer sliding** (`drawer_slide.ogg`): "Drawer Opening & Closing" by quantumriver, CC0 -
  https://freesound.org/people/quantumriver/sounds/552153/

## On-screen controls
- **USE button** (hand) and **joystick knob**: the developer's own pictures (`tools/ui_src/developer`).
- Joystick ring: a plain grey see-through circle (`tools/make_ui.py`); pointer: a circle drawn in code.

## App icon
- Godot's default project icon (Godot logo by Andrea Calabró, CC BY 4.0).

## Engine
- Godot Engine 4.6.2 (MIT licence), GL Compatibility renderer.
