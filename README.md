# Night Class

An original first-person school horror game for Android, made with **Unity 6 (URP)** and built
entirely in the cloud by GitHub Actions (no PC needed).

You wake up at your desk after dark. The school is locked, and the strict old teacher is still
walking the halls with her ruler. You have **5 lessons (lives)** to solve the school and escape.

## How it plays
- Explore a dark school: classrooms, teachers' lounge, toilets, principal's office, library,
  cafeteria, janitor's room, basement and boiler room, gym, garage.
- The teacher patrols, **sees** you in a cone (crouch to be harder to spot), **hears** dropped
  items and loud noises, chases you, opens doors, and drags you out of a locker if she saw you hide.
- **Hide** in lockers and wardrobes, **crawl** through the vent, **crouch**, **jump**.
- Carry **one item at a time**; drop items to distract her.
- **Burn** her with the torch to stop her for 30 seconds.
- Puzzle chain: hammer -> planks, hatch -> basement torch, sprinkler valve -> corridor fire,
  principal's note -> garage keypad, dynamite -> basement rubble, small key -> lounge safe,
  spring -> food elevator, main key -> main door.
- Difficulties: **Ghost** (she can't catch you), **Normal**, **Hard** (faster, sharper eyes,
  thick fog, no ambient sound). A secret room opens after your first escape.

## Build
Every push to the `night-class` branch:
1. downloads CC0 textures from Poly Haven and OFL fonts (`tools/fetch_assets.py`),
2. generates every other asset - decals, UI, the teacher's face, all sounds (`tools/process_assets.py`),
3. builds the whole school, the teacher and the game in Unity from code (`Assets/Editor/NCWorld*.cs`),
4. publishes the APK as a GitHub release `night-class-build-<n>`,
5. plays it in an Android emulator and attaches screenshots to the release.

Repository secrets needed: `UNITY_EMAIL`, `UNITY_PASSWORD` (Unity Personal license).

Credits: textures by Poly Haven (CC0); fonts Barlow, Creepster, Cabin Sketch, Permanent Marker
(Google Fonts, SIL OFL / Apache). All code, models, sounds and other art are original.
