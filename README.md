# Scary Aunty

A simple first-person escape horror game made with **Godot 4.4** (Mobile renderer, Godot's default sun + sky, filmic tone mapping, PBR materials with reflection probes).
Scary Aunty, your neighbour, kidnapped you and locked you in her **3-floor house**. Break the locks, find the objects, solve the safe puzzle and escape through the front door.

The controls copy the SchoolBoy Runaway layout: joystick bottom-left, swipe to look, hint bulb top-left, pause top-right, chalk subtitles at the top, 6 item slots at the bottom and the hand (use) button bottom-right. There is **no crouch / stand button**. The player is fast.

## How to escape
1. Search the nightstand in your room (top floor) and take the **Room Key**. Open your door.
2. Find the **Hammer** in the storage room on the top floor.
3. Break the padlock on Aunty's study (middle floor) with the hammer.
4. Find the 4 **chalk numbers** on the walls (red, blue, green, yellow). Aunty's note in the study tells the order. Open the safe and take the **Main Door Key**. The code is different every game.
5. Take the **Bolt Cutter** from Aunty's bedroom (middle floor).
6. On the front door (ground floor): key opens the padlock, bolt cutter cuts the chain, hammer removes the planks. Open the door and run outside.

Aunty walks around all floors, opens doors, hears loud noises (breaking locks!) and chases you. She catches you 3 times = game over.

## Building (no PC needed)
Every push to the `scary-aunty` branch runs `.github/workflows/scary-aunty.yml` in GitHub Actions. It:
1. downloads the real assets (`ci/fetch_assets.py`):
   - chalk font from **dafont** ("Chalkboard" by Florence S, 100% free)
   - real photo-scanned **CC0 PBR textures** (Poly Haven / ambientCG) - or **your own** images from `assets/user_textures/`
   - Unity footstep sounds, real recorded **CC0 sounds** (Kenney audio packs, Freesound) and music by Kevin MacLeod (CC-BY 4.0)
   - **Sketchfab** 3D models (free CC0 / CC-BY only) for all furniture, items, locks and Aunty
2. imports the project, does a test run to catch script errors,
3. exports `ScaryAunty.apk` and publishes it on the **Releases** page.

### Turn on the Sketchfab models
Sketchfab only allows downloads with your own free account token:
1. On sketchfab.com log in, open **Settings -> Password & API** and copy your **API token**.
2. On GitHub open the repo **Settings -> Secrets and variables -> Actions -> New repository secret**.
   Name: `SKETCHFAB_API_TOKEN`, value: your token.
3. Open **Actions**, pick the last *Scary Aunty APK* run and press **Re-run all jobs**.

Without the token the game still works with simple built-in stand-in models.
The chosen models are saved in `ci/models.lock.json` so every build uses the same ones. To swap a model, put its Sketchfab id there.

### Use your own door / wall / floor textures
Put `door.jpg`, `wall.jpg` and `floor.jpg` in `assets/user_textures/` and push. The build makes normal and roughness maps from them automatically.

## Notes
- `ci/debug.keystore` is a test signing key (like Android's normal debug key). Make a private key before uploading to the Play Store.
- Footsteps are the classic Unity Standard Assets FirstPersonCharacter footsteps (Unity Asset Store EULA), kept in `ci/sounds/`. Locked-door rattles and the drawer sound are CC0 recordings from Freesound.
- Credits for every downloaded asset are shown in the game (main menu -> Credits) and in each release.
