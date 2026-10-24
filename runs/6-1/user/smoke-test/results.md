- Device: sdk_gphone64_x86_64 · Android 14 (API 34)
- Installed DevDarshan-1.0.0-x86_64-TEST.apk
- Launched and still running after 12 s (process started in 14631 ms incl. install wait)
  screenshot: 01-launch.png
- Build is not connected to Firebase yet: the 'Almost ready' gate is shown (expected for test builds)
  screenshot: 02-self-test.png
- In-app self-test passed: ✓ Test image: 1080×2340; ✓ Home screen: set; ✓ Lock screen: set; ✓ Save to gallery: Pictures/DevDarshan
- WallpaperManager state changed (dumpsys wallpaper ids before: User 0: id=0: mWhich=3: mSystemWasBoth=false User 0: id=1: mWhich=1: mSystemWasBoth=false → after: User 0: id=2: mWhich=3: mSystemWasBoth=true User 0: id=3: mWhich=2: mSystemWasBoth=true User 0: id=1: mWhich=1: mSystemWasBoth=false)
- Gallery: Pictures/DevDarshan/DevDarshan-selftest-1792844443980.png exists
- MediaStore: Row: 0 _display_name=DevDarshan-selftest-1792844443980.png, relative_path=Pictures/DevDarshan/
  screenshot: 03-share-sheet.png
- Share sheet opened: topResumedActivity=ActivityRecord{b7460e9 u0 com.android.intentresolver/.ChooserActivity t8}
  screenshot: 04-home-screen-wallpaper.png
- PASSED: no crashes
