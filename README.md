# Arrow Flow v3

A tap-away arrow puzzle for Android, built with React Native (Expo SDK 57) and TypeScript.
Every board is a picture (mushroom, rocket, cat, anchor, butterfly and 60 more) packed with
snake-shaped arrows. Tap one and it slithers out the way its head points, but only if nothing
sits in front of it. Clear the board.

- 300 pre-built levels (each the hardest of six candidates), then endless generated ones;
  Normal, Hard (every 5th) and Super Hard (every 10th) levels; boards up to 28 cells across
- 3 hearts, play clock, arrows-left counter, hints, grid lines, pinch / slider zoom
- Stars, coins, reward chest every 5 levels, daily login rewards (7-day streak), revive
- Daily challenges with monthly trophies, a collection of every shape, arrow colour themes
- Real CC0 sound effects (Kenney "Interface Sounds"), light and dark mode, thin-line option
- In-app Privacy Policy, Terms of Use, Licenses & Credits and About pages
- Fully offline: no internet permission, no ads, no accounts, no analytics

## Getting the APK with only a phone

`.github/workflows/android-apk.yml` builds a release APK on GitHub's servers whenever this
branch is pushed (or from the Actions tab). The APK appears under **Releases** as
`ArrowFlow-v3-<n>.apk`. A second job installs a QA build on an Android emulator, plays through
the main screens and several dense levels, saves screenshots and fails if the app crashes.

## Working on it in VS Code

```bash
npm install
npm test                 # rules, generator, 300 packed levels and a year of daily puzzles
npm run levels           # rebuild src/game/levelPack.ts (deterministic)
npm run typecheck
npm run build:apk        # needs JDK 17 and the Android SDK
```

## Before publishing on Google Play

- Add your contact email in `src/legal/docs.ts` (`contactEmail`); the policy currently points
  people to the email on your Play Store listing.
- Play Console needs a privacy-policy web link; publish the text from the in-app Privacy Policy
  on any web page you control.
- Play only accepts bundles signed with your own upload key; the CI builds here are test APKs.
- Data safety form: the app collects and shares no data. Content rating: puzzle, no violence.

## How it is put together

| Folder | What lives there |
| --- | --- |
| `src/game` | Rules, solver, hints, seeded generator, board shapes, level pack, pixel geometry |
| `src/ui` | Board renderer (zoom, flights), zoom bar, UI kit, theme, icons |
| `src/screens` | Home, Game, Daily, Collection, Trophies, Shop, Settings, legal pages |
| `src/state` | Saved progress (AsyncStorage), economy, dates |
| `src/legal` | Privacy Policy, Terms, Licenses, About text |

**Why it stays smooth on low-end phones.** Resting arrows are plain native views mounted a few
dozen per frame. A tap never re-renders the board: one small description of the move goes to the
UI thread, where a pre-mounted "flight slot" draws the moving arrow with transform-only updates.
Pinch-zoom and pan are UI-thread gestures on a single transformed layer. Levels ship pre-built,
and the next one is prepared while the result screen is showing.

**Levels are solvable by construction.** Arrows are placed in reverse solving order, free arrows
are turned around when that makes them wait for another arrow, then the gaps are packed with
extra arrows, each accepted only if the "waits for" graph stays free of cycles.
