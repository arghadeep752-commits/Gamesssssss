# Camero Plus

A camera and photo/video editor for Android, built with React Native (Expo SDK 54) and a native Kotlin engine on CameraX, OpenGL ES and Media3.

The app only offers what the phone can really do, and labels anything done in software. Nothing is faked: no fake 4K, no fake zoom, no fake RAW, no fake optical stabilization.

## What it does

**Camera**
- Modes: Photo, Video, Pro, Macro, Time-lapse, plus Slow-mo and Portrait on phones whose camera supports them.
- Lens switching, pinch zoom, zoom pills marked optical or digital, tap to focus, long-press AE/AF lock, exposure drag, flash, torch, timer, grid, level, aspect ratios, capture thumbnail.
- Pro controls (ISO, shutter, white balance, manual focus) only where the camera exposes manual sensor control. Focus peaking and zebras.
- Quality sheet lists only the resolutions, frame rates, codecs, HDR, RAW and stabilization options the selected camera supports.
- 35 original looks in five collections (Natural, Everyday, Cinematic, Photography, Film), live in the viewfinder through a GPU shader, with strength control and 17 manual adjustments.

**Software alternatives, always labelled**
- Software stabilization (live and in the editor) on phones without OIS/EIS. It crops about 10%.
- Macro mode on every phone: closest focus, 2× crop, peaking and manual focus when there is no macro lens.
- Upscaled 4K and Smooth 60 (interpolated frames) as video export options. The export sheet says "Upscaled" and "Interpolated".
- RAW is shown only when the camera provides real sensor data (DNG).

**Library and editing**
- Gallery with All, Photos, Videos, Favourites, Edited and Recent; viewer with pinch zoom, video playback, details (EXIF and codec info), share, favourite, delete.
- Photo editor: looks with real previews of the photo, adjustments, crop with aspect ratios, rotate, mirror, undo/redo, hold to compare, full-resolution tiled export.
- Video editor: trim, looks, adjustments, crop, speed, sound, software stabilization, export with resolution, frame rate and codec choices, size estimate, progress and cancel.
- Edits are always saved as new files. Originals are never overwritten.

## Honest limits

- A phone without a 4K sensor mode records at most what its camera offers. "4K" beyond that is an upscaled export and is labelled.
- Smooth 60 creates in-between frames from motion. Fast movement can show soft edges.
- Software stabilization reduces shake but can't match optical stabilization in low light.
- Slow-mo needs the camera's high-speed mode; it isn't offered when the camera has none.
- Portrait mode uses the phone maker's bokeh extension and is hidden when the phone doesn't provide one.
- HDR video sources are converted to SDR when exported from the editor.
- Android 8.0 (API 26) or newer.

## Build

Builds run on GitHub Actions (`.github/workflows/camero-plus.yml`), so no local Android SDK is needed. Each push to the `camero-plus` branch:

1. installs dependencies and type-checks,
2. runs `expo prebuild` and builds the release and debug APKs,
3. verifies both APKs and uploads them as artifacts,
4. publishes a GitHub release when the commit message contains `[release]`.

To build locally instead:

```sh
npm install --legacy-peer-deps
npx expo prebuild --platform android --clean
cd android && ./gradlew :app:assembleRelease
```

Release signing reads `CAMERO_KEYSTORE`, `CAMERO_KEYSTORE_PASSWORD`, `CAMERO_KEY_ALIAS` and `CAMERO_KEY_PASSWORD` from the environment, and falls back to the debug key.

Unit tests (pure logic: crop/rotate math, formatting, lens and mode detection):

```sh
npx tsx --test tests/*.test.ts
```

## Architecture

```
src/                         React Native UI (TypeScript)
  screens/camera             viewfinder, controls, quality sheet, look drawer
  screens/library            gallery, viewer, details
  screens/editor             photo and video editors, crop, timeline, export
  screens/settings           settings, looks, camera report, privacy, licences
  state/                     zustand stores (settings, library, camera, app)
  lib/                       pure helpers (camera logic, grading, transforms)
  ui/                        design system components
modules/camero-engine/       local Expo module (Kotlin)
  camera/                    CameraX session, capability catalog, GL processor
  gl/                        EGL core, shaders, grade program, affine maths
  looks/                     look specs, on-device 3D LUT builder
  edit/                      photo renderer, video exporter, stabilizer,
                             motion estimation, frame interpolation, canvas view
  media/                     MediaStore writer, media probe
```

One grading shader is shared by the live camera, the editor canvas, the full-resolution photo export and the Media3 video export, so what you see is what gets saved.

## Testing checklist

- Camera: every mode, lens switching, zoom pills, pinch zoom, tap focus, AE/AF lock, exposure, flash, torch, timer, grid, level, aspect ratios.
- Quality sheet shows only supported options; changing them rebinds the camera.
- Looks live in the viewfinder, at different strengths; capture with and without "Keep an untouched copy".
- Video: record, pause, resume, mute; software stabilization label on phones without OIS/EIS.
- Gallery filters, favourites, delete (system confirmation on Android 11+), share to another app.
- Photo editor: looks, adjustments, crop/rotate/mirror, undo/redo, compare, save copy.
- Video editor: trim, speed, mute, stabilize, upscaled 4K and Smooth 60 export, cancel export.
- Permissions: deny and re-allow camera, microphone and media access.
