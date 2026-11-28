# Arrow Flow v2

A tap-away arrow puzzle for Android, built with React Native (Expo SDK 57) and TypeScript.
Snake-shaped arrows fill the board; tap one and it slithers out the way its head points, its body
following its own trail. It can only leave if nothing sits in front of its head. Clear the board.

- Endless levels (the same puzzle on every phone), growing from 3x3 to 12x15 boards, with
  shaped boards (circle, heart, diamond, ring, plus, hexagon, hourglass, rounded)
- 3 hearts per level, a blocked tap costs one; no timer
- Hints that light up an arrow which can leave right now (earned by playing)
- Daily challenges on a calendar, harder toward the weekend, with a monthly trophy for solving
  every day of a month, plus a trophy room and stats
- Light and dark themes, sound, music and vibration settings; fully offline, no ads, no accounts

## Getting the APK with only a phone

`.github/workflows/android-apk.yml` builds a release APK on GitHub's servers. Push this project to
the `arrow-flow-v2` branch (or run the workflow from the Actions tab). After about 15-25 minutes
the APK appears under **Releases** as `ArrowFlow-v2-<n>.apk`.

## Working on it in VS Code

```bash
npm install
npm test                 # rules, generator, 400 levels and a year of daily puzzles
npm run typecheck
npm run build:apk        # needs JDK 17 and the Android SDK
```

## How it is put together

| Folder | What lives there |
| --- | --- |
| `src/game` | Pure TypeScript rules: blocking, solver, hints, the seeded level generator, board shapes, pixel geometry |
| `src/ui` | Board renderer, UI kit, theme, icons |
| `src/screens` | Home, Game, Daily, Trophies, Settings |
| `src/state` | Saved progress (AsyncStorage) and date helpers |
| `src/services` | Sound and vibration |

**Why it stays smooth on low-end phones.** Resting arrows are plain native views created once
per level. A tap never re-renders the board: it sends one small description of the move to the UI
thread, where a pre-mounted "flight slot" draws the moving arrow using only transform and opacity
changes, and the resting copy is hidden in the same frame. The slither is computed per frame from a
single animated number (`pieceFrame` in `src/game/geometry.ts`). Puzzles are generated in a few
milliseconds and the next one is prepared while the result screen is showing.

**Levels are solvable by construction.** Arrows are placed in reverse solving order and each new
arrow must have an empty line in front of its head, then some free arrows are turned around when
that makes them wait for another arrow and the board stays solvable. Because removing arrows only
frees cells, any free arrow is always a safe move.
