# TRADER'S MADNESS (Unity 6)

A first-person escape horror game for Android. You are trapped in a binary trader's two-storey modern house. He
lost everything on one trade and blames you. Get out through the front door within five days.

## The front door

Three barriers keep it shut, in any order:

1. **Three wooden planks**: pry them off with the **claw hammer**. The hammer is in the **garage**, which is locked:
   the **garage key** lies somewhere in the kitchen or living room.
2. **Gold padlock**: the **gold key** is in the **safe** in the master bedroom. The safe's code is engraved on the
   **"Top Trader" trophy** on the trading room shelf.
3. **Silver padlock**: the **silver key** is in the locked drawer of the **trading desk**. Its **small key** is
   buried in one of the two **plant pots**.
4. **Door code**: the trading room has no power. Find the **fuse** (utility room or bathroom), put it into the
   **fuse box** in the garage, and the trader's **gaming PC** with six monitors boots up. The six-digit door code is
   on a sticky note on his screen.

Codes and item places change every game. Wrong codes beep loudly; dropping things, prying planks and opening doors
make noise. Hide in the wardrobes. Easy / Normal / Hard = low / medium / high risk.

## How it is built (no PC needed)

`.github/workflows/traders-madness.yml` runs on every push to this branch:

| job | what it does |
|---|---|
| `assets` | photo-scanned CC0 textures (Poly Haven, ambientCG), a photographed night sky, real recorded sounds (Openverse / Wikimedia Commons / Internet Archive) - `tools/fetch_assets.py` |
| `rodin` | the Hyper3D Rodin models (furniture, props, the rigged and animated trader) - `tools/rodin_fetch.py`, list in `tools/rodin/models.json` |
| `house` | Blender 4.2 builds the house from code (`tools/house/`), fits the Hyper3D models into their places and bakes the night lighting (twice for the trading room: power off / on) |
| `compile` | a quick check that every C# script compiles |
| `apk` | `tools/unity/convert_assets.py`, then Unity 6000.0 (batch mode) runs `TradersMadness.EditorTools.TMBuild.BuildAndroid` and publishes the APK as the release `traders-madness-v<n>` |
| `emulator` | an emulator build plays through the game and attaches its screenshots to the release |

`tools/house/preview_plan.py` draws both floor plans (walls, doors, furniture, items, the trader's patrol and walk
grid); `tools/house/offline_export.py` writes the house without Blender for checking the Unity conversion.

## Code

| file | |
|---|---|
| `Assets/Scripts/Game.cs` | menus (trading-terminal style), intro, days, interactions, keypads, the PC screen, caught / escaped |
| `Assets/Scripts/Level.cs` | the house: colliders, doors, items, the puzzles, power, the walk grid over both floors and the stair |
| `Assets/Scripts/Enemy.cs` | the trader: patrol, hearing, sight, chase up and down the stairs, the punch |
| `Assets/Scripts/Player.cs`, `Hud.cs` | first-person touch controls: joystick, drag to look, hand, crouch, drop, pause |
| `Assets/Scripts/Screens.cs`, `MenuChart.cs` | the monitors' live charts and the menu's candlestick chart |
| `Assets/Shaders/` | photo texture x baked light (House), the trader (Character), glass, glowing screens |
| `Assets/Editor/` | builds the house and trader prefabs from the converted files, sets up and builds the APK |

Fonts: Bebas Neue, Anton, Rajdhani, Share Tech Mono (SIL Open Font License).
