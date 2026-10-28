# Arrow Flow

A minimalist arrow puzzle game for Android, built with React Native, Expo SDK 57 and TypeScript.
Tap an arrow and it slides off the board the way it points, but only if nothing stands in its path.
Find the order and clear the board.

- 100 verified levels in five tiers (Tutorial, Easy, Normal, Hard, Expert)
- Daily Challenge generated from the date, fully offline, with streaks
- Hearts, real hints (always a legal move), Scan path helper, Undo, Restart, Pause
- Three-star scoring, best results, level unlocking, achievements and tier medals
- Versioned local saves with recovery; no network, accounts, ads or analytics
- Original vector art and synthesized sounds (about 230 KB of audio in total)

## Getting an APK with only a phone

The project includes a GitHub Actions workflow (`.github/workflows/android-apk.yml`) that builds an
installable release APK on GitHub's servers.

1. Put this project in a GitHub repository (on the `main`, `master` or `arrow-flow` branch).
2. Open the repository's **Actions** tab. The "Build Android APK" run starts on every push; you can also
   start it with **Run workflow**. A build takes roughly 15-30 minutes.
3. When it finishes, open **Releases** (or the run's Summary). Download `ArrowFlow-<n>.apk` on your phone and
   open it. Android will ask you to allow installing apps from your browser the first time.

The run also type-checks the code, runs the test suite and validates every level before building, and its
Summary lists the APK size, the largest files inside it and the permissions it requests.

These test builds are signed with the standard debug key, which is fine for installing on your own phone but
not for the Play Store (see "Before publishing").

Other ways to build:

- **EAS Build**: `npx eas-cli build -p android --profile preview` produces an APK (`production` produces an AAB).
- **Local**: with Node 22, JDK 17 and the Android SDK installed, `npm install && npm run build:apk`.

## Development

```bash
npm install
npm run verify          # type-check + unit tests + level validation
npm start               # Metro; use a development build (native modules are included)
```

| Script | What it does |
| --- | --- |
| `npm test` | Engine, solver, session, scoring, save/progress, daily and rendering-geometry tests (`node --test`) |
| `npm run typecheck` | App code and node-side scripts/tests |
| `npm run levels:validate` | Validates all shipped levels plus 400 days of daily puzzles; fails on any problem |
| `npm run levels:build` | Regenerates `src/levels/data/packedLevels.ts` (deterministic) |
| `npm run sounds` | Re-synthesizes the sound effects and music loop (Python + numpy, ffmpeg) |
| `npm run icons` | Re-renders the launcher icon, adaptive icon and splash image (needs `sharp`) |

## How the puzzle works

All rules live in `src/game` (pure TypeScript, no React) and are shared by gameplay, hints, the Scan tool,
the solver and the level tools.

- The board is a grid of cells. An arrow is an ordered path of adjacent cells, tail first, head last, at least
  two cells long. Its exit direction is the direction of its last step.
- Each cell holds at most one arrow, so arrows never cross.
- An arrow leaves by sliding its whole shape, unchanged, in its exit direction.
- Its **corridor** is every cell any of its cells passes through on the way out. It is **blocked** while any
  other active arrow sits in the corridor.
- Removing arrows only frees cells, so a free arrow stays free. The blocking relation is therefore fixed by the
  starting layout, a level is solvable exactly when that relation has no cycle, and any free arrow is always a
  correct next move. The solver is a linear-time greedy pass.

Validation (`src/game/validate.ts`) checks ids, bounds, path continuity, head direction, overlaps,
solvability, and cross-checks the corridor engine against an independent step-by-step simulation.

### Levels

`scripts/build-levels.ts` generates many seeded candidates per level slot with `src/game/generator.ts` (solvable
by construction: each new arrow must have an empty corridor when placed), rejects anything that fails
validation, and keeps the candidate closest to the difficulty curve in `src/levels/tierParams.ts`. Levels 1-3
are hand-authored teaching levels. Output is compact text, about 13 KB for 100 levels.

| Tier | Levels | Avg arrows | Avg dependency depth |
| --- | --- | --- | --- |
| Tutorial | 1-10 | 6.0 | 2.5 |
| Easy | 11-25 | 11.5 | 3.5 |
| Normal | 26-50 | 17.8 | 5.0 |
| Hard | 51-75 | 23.6 | 7.0 |
| Expert | 76-100 | 26.9 | 9.1 |

The daily puzzle uses the same generator seeded by the local date (`src/levels/daily.ts`); Monday is easy,
weekends are expert.

## Rules you can tune

`src/config/gameConfig.ts`:

- 3 hearts per attempt. Tapping a blocked arrow costs a heart (a deliberate rule: hearts are the only failure
  condition). Tutorial levels count the mistake but never cost a heart. Set `blockedTapCostsLife: false` to
  turn hearts off.
- Stars: penalty = mistakes + hints + half of any extra moves from Undo. 0 gives 3 stars, up to 2 gives 2 stars.
  Best results are only replaced by strictly better ones.
- 3 Scan uses per attempt, 5 starting hints, +1 hint the first time every fifth level is cleared, +1 to +3 for
  each Daily Challenge (once per day).

## App structure

```
index.ts                  entry (registerRootComponent)
src/app/                  App root, error boundary, tiny stack navigator with Android back handling
src/game/                 engine, solver, generator, validation, session rules, scoring (pure TS)
src/levels/               packed level data, level lookup, daily puzzle, difficulty curve
src/state/                save schema + migration, progress transitions, achievements, store
src/storage/              AsyncStorage persistence with backup and recovery
src/services/             audio (expo-audio), haptics (expo-haptics), future rewarded-ads seam
src/components/           Board, ArrowView (Reanimated), icons, buttons, sheets, UI primitives
src/screens/              Home, Levels, Game, Daily, Me, Achievements, Settings, Help, Legal, Privacy
src/utils/                drawing geometry and hit testing (pure, tested)
scripts/                  level builder/validator, sound and icon generators
test/                     node:test suites
```

Performance notes:

- One touch responder for the whole board, resolved through the engine's cell grid on touch-down. Empty cells
  next to an arrow still select it, which gives thin arrows a generous hit area.
- Each arrow is its own small SVG inside an `Animated.View`; exit glides (250-400 ms) and blocked bumps are
  Reanimated animations on the UI thread. Only the tapped arrow re-renders.
- The puzzle state changes the moment a move is validated, and the arrow then glides out
  (IDLE -> MOVING -> REMOVED), so quick players are never blocked by an arrow that is already leaving.
- Saves are debounced, written in order, and flushed when the app goes to the background. The unfinished puzzle
  is replayed through the engine on load, so a damaged save can never produce an impossible board.
- Release builds enable R8 minification and resource shrinking and ship only ARM ABIs (`app.json`).

## Before publishing

- Replace the developer name and contact placeholders in `src/config/appInfo.ts` (all legal screens read them).
- Change the Android package id in `app.json` (`com.arrowflow.puzzle`) to one you own.
- Create a release keystore (or use EAS credentials); the CI APK is debug-signed for testing only.
- If you ever add a network, analytics or ads SDK, update `src/config/legal.ts` first.

## Verification status

Checked in the environment this project was written in:

- 69 automated tests pass; all 100 levels and 400 daily puzzles validate; level generation is reproducible.
- All app code type-checks against React Native 0.86.3, React 19 and the Expo SDK 57 module type definitions.
  react-native-svg, Reanimated, safe-area-context and AsyncStorage were checked against hand-written type stubs
  of their public APIs, because their packages could not be installed there.
- A browser build of the same engine, levels and rules was played through end to end.

Not yet checked: a native Android build, the final APK size, and profiling on real devices. The GitHub Actions
workflow is the first full native build; check its log if it fails.
