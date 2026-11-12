# ASSET CREDITS — Ninja: Shadow Legacy (MXYAN GAMES)

Every graphic and sound in this project was made by a human artist and released under
**CC0 1.0 (public domain)**. No AI-generated art or audio is used. CC0 does not require
attribution, but all creators are credited here and in the in-game Credits screen.

> **How the files were obtained.** The build machine could only reach GitHub (kenney.nl,
> itch.io, OpenGameArt, CraftPix, Freesound and Pixabay were blocked). The packs below were
> therefore downloaded from public GitHub copies of the original CC0 packs. Because CC0 allows
> redistribution, those copies are legitimate. Licences were checked on the original pages
> where they could be reached (noted below).

| Asset | Creator | Original source | Licence | Attribution | Downloaded from |
|---|---|---|---|---|---|
| "Ninja Adventure – Free Sprite" (ninja boy: idle, run, jump, attack, jump-attack, throw, jump-throw, glide, climb, slide, dead) + kunai | Zuhria Alfitra (pzUH), GameArt2D | https://www.gameart2d.com/freebies.html · https://opengameart.org/content/ninja-adventure-free-sprite | CC0 (GameArt2D licence page: freebies are "Creative Commons Zero (CC0) / Public Domain") | Not required | github.com/nawan44/Unity-Game-2D-Adventure (`Assets/2d art/ninjaadventurenew`) |
| New Platformer Pack — terrain tiles (grass, dirt, snow, stone, purple), props, coins, gems, hearts, flags, ladders, spikes, springs, saws, lava, water, doors, torches, weights, enemies (slimes, bee, fly, frog, ladybug, mouse, snail, worms, barnacle, fish), backgrounds | Kenney (kenney.nl) | https://kenney.nl/assets/new-platformer-pack | CC0 | Not required | github.com/Tiddybub/2d-assets (`characters/new-platformer-pack`) |
| Background Elements (Remastered) — trees, houses, towers, castles, sun/moon, clouds | Kenney | https://kenney.nl/assets/background-elements-redux | CC0 | Not required | github.com/Tiddybub/2d-assets (`tiles-terrain/background-elements-remastered`) |
| UI Pack — buttons, sliders, checkboxes, stars | Kenney | https://kenney.nl/assets/ui-pack | CC0 | Not required | github.com/Tiddybub/2d-assets (`ui/ui-pack`) |
| UI Pack (Adventure) — panels, banners, progress bars, round frames | Kenney | https://kenney.nl/assets/ui-pack-adventure | CC0 | Not required | github.com/Tiddybub/2d-assets (`ui/ui-pack-adventure`) |
| Mobile Controls — joystick pad/nub, round buttons, control icons | Kenney | https://kenney.nl/assets/mobile-controls | CC0 | Not required | github.com/Tiddybub/2d-assets (`ui/mobile-controls`) |
| Game Icons (white) | Kenney | https://kenney.nl/assets/game-icons | CC0 | Not required | github.com/ETdoFresh/kenney.nl (`gameicons`) |
| Kenney Fonts (Kenney Future, Future Narrow, Blocks, Rocket) | Kenney | https://kenney.nl/assets/kenney-fonts | CC0 | Not required | github.com/Tiddybub/2d-assets (`ui/kenney-fonts`) |
| Particle Pack — slashes, sparks, stars, flames, smoke, magic, lights | Kenney | https://kenney.nl/assets/particle-pack | CC0 | Not required | github.com/Tiddybub/2d-assets (`effects/particle-pack`) |
| RPG Audio (footsteps, knife slices, cloth, coins, door) | Kenney | https://kenney.nl/assets/rpg-audio | CC0 | Not required | github.com/ETdoFresh/kenney.nl (`kenney_rpgaudio`) |
| Impact Sounds | Kenney | https://kenney.nl/assets/impact-sounds | CC0 | Not required | github.com/ETdoFresh/kenney.nl (`kenney_impactsounds`) |
| Interface Sounds | Kenney | https://kenney.nl/assets/interface-sounds | CC0 | Not required | github.com/ETdoFresh/kenney.nl (`kenney_interfacesounds`) |
| Voiceover Pack: Fighter ("Fight!", "You win", "Ready", "Game over") | Kenney | https://kenney.nl/assets/voiceover-pack-fighter | CC0 | Not required | github.com/ETdoFresh/kenney.nl (`kenney_voiceoverfighter`) |
| Ninja Adventure Asset Pack — 12 music tracks (Adventure Begin, Adventure, Lost Village, Ascension, Temple, Dark Castle, Curse, Fight ×2, Final Area, Credit Theme, End Theme), sound effects, jingles | Pixel-boy & AAA | https://pixel-boy.itch.io/ninja-adventure-asset-pack | CC0 (LICENSE.txt + README in pack) | Not required ("appreciated") | github.com/DaltonCarter/GoDot-Ninja-Adventure (`Ninja Adventure - Asset Pack`) |
| Ninja Adventure — weapon icons (Katana, Sai, Bow, Big Sword), shuriken / arrow / fireball / ice-spike / big-kunai projectiles, treasure chest, pixel FX and particles (sakura petals, leaves, snow, embers) | Pixel-boy & AAA | https://pixel-boy.itch.io/ninja-adventure-asset-pack | CC0 | Not required | github.com/DaltonCarter/GoDot-Ninja-Adventure |

Engine: **Godot Engine 4.5.1** — MIT licence (https://godotengine.org/license). The licence text
is shown on the Credits screen link and must accompany distributed builds per the MIT terms.

## Modifications made (allowed by CC0)
* Ninja frames were down-scaled 25 % and re-packed into aligned strips (`tools/build_assets.py`).
* Character variants, skins, enemy ninjas and the ninja-type bosses re-dye the artist's purple cloth
  in a shader (`shaders/sprite_fx.gdshader`). See "Asset gaps" below.
* Kenney background images had their white sky removed so they work as parallax layers.
* Pixel-art icons/projectiles were enlarged with nearest-neighbour scaling.
* The app icon is composed from the CC0 ninja artwork.

## Asset gaps — please review / approve replacements
The PRD asks for unique sprites for every character and boss. No reachable CC0 source provided
matching-style sprite sets for these, so the following use the real artist sprites above in
modified form instead of placeholders. Each is a single file/slot to swap if you obtain new art:

1. **Shadow / Samurai / Fire / Ice Ninja** use the same ninja animation set with different
   cloth/armour colours and their own aura particles, stats and special attacks.
2. **Shadow Samurai, Demon Ronin, Shadow King** are enlarged, re-dyed versions of the ninja.
3. **Ice Guardian, Temple Beast, Fire Lord** are giant re-coloured Kenney slime creatures.
4. **Bow** has no draw animation in the artist set; it uses the throw animation.
5. Weapon icons, projectiles and the chest are pixel art, a small style mix with the vector art.
