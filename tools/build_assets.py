"""Asset pipeline for NINJA: SHADOW LEGACY.

Copies and optimizes CC0 source assets (already downloaded from GitHub mirrors)
into the Godot project. Every source used here is listed in ASSET_CREDITS.md.
"""
import colorsys
import json
import os
import shutil
import subprocess
import sys

from PIL import Image

SRC = "/home/claude/assets_src"
PRJ = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/ninja_shadow_legacy"
A = os.path.join(PRJ, "assets")

NINJA = f"{SRC}/nawan44_Unity-Game-2D-Adventure/Assets/2d art/ninjaadventurenew"
NPP = f"{SRC}/tiddy/characters/new-platformer-pack/Sprites"
UIP = f"{SRC}/tiddy/ui/ui-pack/PNG"
UIA = f"{SRC}/tiddy/ui/ui-pack-adventure/PNG/Double"
MOB = f"{SRC}/tiddy/ui/mobile-controls/Sprites"
FONTS = f"{SRC}/tiddy/ui/kenney-fonts/Fonts"
PART = f"{SRC}/tiddy/effects/particle-pack/PNG (Transparent)"
BGE = f"{SRC}/tiddy/tiles-terrain/background-elements-remastered/PNG/Default"
NA = f"{SRC}/DaltonCarter_GoDot-Ninja-Adventure/Ninja Adventure - Asset Pack"
KEN = f"{SRC}/kenney"


def mk(*p):
    d = os.path.join(A, *p)
    os.makedirs(d, exist_ok=True)
    return d


def cp(src, dst_dir, name=None):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name or os.path.basename(src))
    shutil.copyfile(src, dst)
    return dst


# ---------------------------------------------------------------- ninja hero
NINJA_ANIMS = {
    # name: (file prefix, fps, loop)
    "idle": ("Idle__", 12, True),
    "run": ("Run__", 16, True),
    "jump": ("Jump__", 14, False),
    "attack": ("Attack__", 26, False),
    "jump_attack": ("Jump_Attack__", 26, False),
    "throw": ("Throw__", 24, False),
    "jump_throw": ("Jump_Throw__", 24, False),
    "glide": ("Glide_", 12, True),
    "climb": ("Climb_", 12, True),
    "slide": ("Slide__", 18, True),
    "dead": ("Dead__", 14, False),
}
NINJA_SCALE = 0.25
FOOT_MARGIN = 4


def skin_com(im):
    """Centre of the face (skin-coloured pixels) -> stable horizontal anchor."""
    px = im.load()
    w, h = im.size
    sx = n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, a = px[x, y]
            if a < 200:
                continue
            hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if 0.06 < hh < 0.16 and 0.15 < s < 0.65 and v > 0.75:
                sx += x
                n += 1
    return sx / n if n > 20 else None


def build_ninja():
    out = mk("characters", "ninja")
    meta = {}
    frames_by_anim = {}
    for anim, (prefix, fps, loop) in NINJA_ANIMS.items():
        files = sorted(f for f in os.listdir(f"{NINJA}/png") if f.startswith(prefix) and f.endswith(".png"))
        if prefix == "Jump__":
            files = [f for f in files if not f.startswith("Jump_Attack") and not f.startswith("Jump_Throw")]
        ims = []
        for f in files:
            im = Image.open(f"{NINJA}/png/{f}").convert("RGBA")
            w, h = im.size
            im = im.resize((round(w * NINJA_SCALE), round(h * NINJA_SCALE)), Image.LANCZOS)
            ims.append(im)
        frames_by_anim[anim] = ims
    # anchors
    anchors = {}
    for anim, ims in frames_by_anim.items():
        xs = [c for c in (skin_com(im) for im in ims) if c is not None]
        xs.sort()
        ax = xs[len(xs) // 2] if xs else ims[0].size[0] / 2
        bottom = max(im.getbbox()[3] for im in ims)
        top = min(im.getbbox()[1] for im in ims)
        anchors[anim] = (ax, bottom, top)
    cell_h = max(anchors[a][1] - anchors[a][2] for a in anchors) + FOOT_MARGIN + 6
    for anim, ims in frames_by_anim.items():
        ax, bottom, top = anchors[anim]
        half = 0
        for im in ims:
            bb = im.getbbox()
            half = max(half, ax - bb[0], bb[2] - ax)
        cw = int(2 * half + 4)
        cw += cw % 2
        strip = Image.new("RGBA", (cw * len(ims), cell_h), (0, 0, 0, 0))
        for i, im in enumerate(ims):
            ox = int(round(i * cw + cw / 2 - ax))
            oy = int(cell_h - FOOT_MARGIN - bottom)
            strip.alpha_composite(im, (max(0, ox) if ox >= i * cw else ox, oy))
        strip.save(os.path.join(out, f"{anim}.png"), optimize=True)
        _, fps, loop = NINJA_ANIMS[anim]
        meta[anim] = {"frames": len(ims), "w": cw, "h": cell_h, "fps": fps, "loop": loop}
    meta["_foot_margin"] = FOOT_MARGIN
    with open(os.path.join(out, "ninja_frames.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    # kunai (vertical source -> horizontal projectile)
    k = Image.open(f"{NINJA}/Kunai/Kunai.png").convert("RGBA").rotate(-90, expand=True)
    k = k.resize((int(k.size[0] * 0.42), int(k.size[1] * 0.42)), Image.LANCZOS)
    k.save(os.path.join(mk("weapons"), "kunai.png"))
    print("ninja", {a: (m["frames"], m["w"], m["h"]) for a, m in meta.items() if not a.startswith("_")})


# --------------------------------------------------------------- environment
TERRAINS = ["grass", "dirt", "snow", "stone", "sand", "purple"]
TILE_ORDER = [
    "block_top_left", "block_top", "block_top_right",
    "block_left", "block_center", "block_right",
    "block_bottom_left", "block_bottom", "block_bottom_right",
    "block", "horizontal_left", "horizontal_middle", "horizontal_right",
    "cloud_left", "cloud_middle", "cloud_right",
]


def build_tiles():
    out = mk("environments", "tiles")
    T = 64
    atlas = Image.new("RGBA", (T * len(TILE_ORDER), T * len(TERRAINS)), (0, 0, 0, 0))
    for r, terr in enumerate(TERRAINS):
        for c, piece in enumerate(TILE_ORDER):
            im = Image.open(f"{NPP}/Tiles/Default/terrain_{terr}_{piece}.png").convert("RGBA")
            atlas.alpha_composite(im, (c * T, r * T))
    atlas.save(os.path.join(out, "terrain_atlas.png"), optimize=True)
    props = mk("environments", "props")
    names = [
        "coin_gold", "coin_gold_side", "coin_silver", "coin_bronze", "gem_blue", "gem_green", "gem_red", "gem_yellow",
        "heart", "star", "key_yellow", "key_blue", "lock_yellow", "flag_off", "flag_red_a", "flag_red_b", "flag_green_a", "flag_green_b",
        "ladder_top", "ladder_middle", "ladder_bottom", "spikes", "spring", "spring_out", "saw", "lava", "lava_top", "lava_top_low",
        "water", "water_top", "water_top_low", "torch_on_a", "torch_on_b", "torch_off", "sign", "sign_exit", "sign_right", "door_open", "door_open_top",
        "door_closed", "door_closed_top", "bridge", "bridge_logs", "fence", "fence_broken", "bush", "cactus", "rock", "mushroom_red", "mushroom_brown",
        "snow", "chain", "weight", "block_planks", "block_plank", "block_coin", "block_coin_active", "block_strong_danger", "block_spikes",
        "bomb", "bomb_active", "fireball", "switch_red", "switch_red_pressed", "lever_left", "lever_right", "window", "grass", "grass_purple",
        "hill", "hill_top", "brick_brown", "bricks_brown", "brick_grey", "bricks_grey", "conveyor", "rop_attached", "rope",
        "block_empty", "block_exclamation", "block_red", "block_blue", "block_green", "block_yellow",
    ]
    for n in names:
        cp(f"{NPP}/Tiles/Default/{n}.png", props)
    for n in ["hud_coin", "hud_heart", "hud_heart_empty", "hud_heart_half", "hud_key_yellow"]:
        cp(f"{NPP}/Tiles/Default/{n}.png", mk("ui", "hud"))
    print("tiles ok")


ENEMY_FRAMES = [
    "slime_normal_rest", "slime_normal_walk_a", "slime_normal_walk_b", "slime_normal_flat",
    "slime_spike_rest", "slime_spike_walk_a", "slime_spike_walk_b", "slime_spike_flat",
    "slime_fire_rest", "slime_fire_walk_a", "slime_fire_walk_b", "slime_fire_flat",
    "slime_block_rest", "slime_block_walk_a", "slime_block_walk_b", "slime_block_jump",
    "bee_a", "bee_b", "bee_rest", "fly_a", "fly_b", "fly_rest", "frog_idle", "frog_jump", "frog_rest",
    "ladybug_walk_a", "ladybug_walk_b", "ladybug_fly", "ladybug_rest", "mouse_walk_a", "mouse_walk_b", "mouse_rest",
    "snail_walk_a", "snail_walk_b", "snail_shell", "snail_rest", "worm_normal_move_a", "worm_normal_move_b", "worm_normal_rest",
    "worm_ring_move_a", "worm_ring_move_b", "worm_ring_rest", "barnacle_attack_a", "barnacle_attack_b", "barnacle_attack_rest",
    "saw_a", "saw_b", "saw_rest", "fish_purple_up", "fish_purple_down", "fish_purple_rest", "block_idle", "block_fall", "block_rest",
]
BOSS_FRAMES = [n for n in ENEMY_FRAMES if n.startswith(("slime_block", "slime_spike", "slime_fire"))]


def build_enemies():
    out = mk("enemies")
    for n in ENEMY_FRAMES:
        cp(f"{NPP}/Enemies/Default/{n}.png", out)
    bout = mk("bosses")
    for n in BOSS_FRAMES:
        cp(f"{NPP}/Enemies/Double/{n}.png", bout)
    cp(f"{NPP}/Tiles/Double/fireball.png", bout, "fireball_big.png")
    print("enemies ok")


BG_ELEMENTS = [
    "tree", "treeLong", "treePine", "treeSmall_green1", "treeSmall_green2", "bush1", "bush2", "cloud1", "cloud2", "cloud3",
    "cloud5", "cloud6", "cloud8", "sun", "moon", "moonFull", "house1", "house2", "houseAlt1", "houseSmall1", "houseSmall2",
    "fence", "fenceIron", "treeOrange", "treeLongOrange", "treePineOrange", "treeFrozen", "treePineFrozen", "treePineSnow",
    "treeSnow", "treeLongSnow", "treeLongFrozen", "treeDead", "tower", "towerAlt", "towerSmall", "towerSmallAlt",
    "castleSmall", "castleSmallAlt", "castleWall", "castleWallAlt", "pyramid", "cactus1",
]


def build_backgrounds():
    out = mk("backgrounds")
    for f in os.listdir(f"{NPP}/Backgrounds/Default"):
        cp(f"{NPP}/Backgrounds/Default/{f}", out)
    el = mk("backgrounds", "elements")
    for n in BG_ELEMENTS:
        cp(f"{BGE}/{n}.png", el)
    print("backgrounds ok")


# ------------------------------------------------------------------------ UI
def build_ui():
    out = mk("ui")
    for color in ["Blue", "Green", "Red", "Yellow", "Grey"]:
        d = mk("ui", "buttons", color.lower())
        for n in ["button_rectangle_depth_gloss", "button_rectangle_depth_flat", "button_rectangle_flat", "button_rectangle_gloss",
                  "button_round_depth_gloss", "button_round_gloss", "button_square_depth_gloss", "button_square_gloss",
                  "check_square_color_checkmark", "check_square_grey", "slide_horizontal_color", "slide_horizontal_grey",
                  "slide_hangle", "star", "star_outline", "arrow_basic_e", "arrow_basic_w", "arrow_decorative_e", "arrow_decorative_w",
                  "icon_checkmark", "icon_cross"]:
            p = f"{UIP}/{color}/Double/{n}.png"
            if os.path.exists(p):
                cp(p, d)
    pd = mk("ui", "panels")
    for n in ["panel_brown", "panel_brown_dark", "panel_brown_corners_a", "panel_brown_dark_corners_a", "panel_grey_dark",
              "panel_grey", "panel_border_brown", "panel_border_grey", "banner_hanging", "banner_modern", "banner_classic_curtain",
              "progress_red", "progress_red_border", "progress_green", "progress_green_border", "progress_blue", "progress_blue_border",
              "progress_white", "progress_white_border", "progress_transparent", "button_brown", "button_grey", "button_red",
              "button_brown_close", "button_red_close", "round_brown", "round_grey_dark", "hexagon_brown", "hexagon_grey_dark",
              "minimap_icon_star_yellow", "minimap_icon_jewel_red", "minimap_icon_exclamation_yellow", "minimap_ring_brown",
              "scrollbar_brown", "checkbox_brown_checked", "checkbox_brown_empty"]:
        p = f"{UIA}/{n}.png"
        if os.path.exists(p):
            cp(p, pd)
    cd = mk("ui", "controls")
    for n in ["joystick_circle_pad_a", "joystick_circle_pad_b", "joystick_circle_nub_a", "joystick_circle_nub_b",
              "button_circle", "button_hexagon", "button_square", "button_bean"]:
        cp(f"{MOB}/Style A/Large (2×)/{n}.png", cd, "a_" + n + ".png")
        p = f"{MOB}/Style B/Large (2×)/{n}.png"
        if os.path.exists(p):
            cp(p, cd, "b_" + n + ".png")
    idir = mk("ui", "icons")
    for f in os.listdir(f"{MOB}/Icons/Large (2×)"):
        cp(f"{MOB}/Icons/Large (2×)/{f}", idir)
    gi = f"{KEN}/gameicons/PNG/White/2x"
    if os.path.isdir(gi):
        for n in ["home", "gear", "pause", "right", "left", "return", "trophy", "star", "locked", "unlocked", "musicOn", "musicOff",
                  "audioOn", "audioOff", "shoppingCart", "cross", "checkmark", "exitLeft", "information", "menuGrid", "power",
                  "medal1", "medal2", "leaderboardsComplex", "plus", "minus", "massiveMultiplayer", "singleplayer", "target",
                  "fastForward", "forward", "next", "previous", "buttonStart", "share", "question", "wrench", "warning"]:
            p = f"{gi}/{n}.png"
            if os.path.exists(p):
                cp(p, idir, "gi_" + n + ".png")
    fd = mk("..", "fonts")
    for n in ["Kenney Future.ttf", "Kenney Future Narrow.ttf", "Kenney Blocks.ttf", "Kenney Rocket.ttf"]:
        cp(f"{FONTS}/{n}", fd, n.replace(" ", "_"))
    print("ui ok")


# -------------------------------------------------------------------- effects
def build_effects():
    out = mk("effects")
    want = ["slash_01", "slash_02", "slash_03", "slash_04", "star_01", "star_04", "star_06", "star_07", "spark_01", "spark_04",
            "spark_05", "spark_06", "flame_01", "flame_03", "flame_05", "fire_01", "magic_01", "magic_02", "magic_04", "magic_05",
            "smoke_01", "smoke_04", "smoke_07", "circle_02", "circle_05", "light_01", "light_03", "trace_01", "trace_04",
            "twirl_01", "twirl_02", "scorch_02", "dirt_02", "muzzle_02", "flare_01", "symbol_02", "window_03"]
    for n in want:
        im = Image.open(f"{PART}/{n}.png").convert("RGBA")
        im = im.resize((128, 128), Image.LANCZOS)
        im.save(os.path.join(out, n + ".png"), optimize=True)
    # Ninja Adventure projectile + weapon pixel art (CC0) -> upscaled with nearest
    wd = mk("weapons")

    def up(src, name, factor):
        im = Image.open(src).convert("RGBA")
        im = im.resize((im.size[0] * factor, im.size[1] * factor), Image.NEAREST)
        im.save(os.path.join(wd, name))

    up(f"{NA}/FX/Projectile/BigShuriken.png", "shuriken_sheet.png", 3)
    up(f"{NA}/FX/Projectile/Arrow.png", "arrow.png", 4)
    up(f"{NA}/FX/Projectile/Fireball.png", "fireball_sheet.png", 3)
    up(f"{NA}/FX/Projectile/IceSpike.png", "icespike_sheet.png", 3)
    up(f"{NA}/FX/Projectile/BigKunai.png", "big_kunai.png", 3)
    for w in ["Katana", "Sai", "Bow", "Ninjaku", "BigSword", "Lance"]:
        up(f"{NA}/Items/Weapons/{w}/Sprite.png", f"icon_{w.lower()}.png", 8)
    up(f"{NA}/FX/Projectile/Shuriken.png", "icon_shuriken.png", 6)
    ef = mk("effects", "pixel")
    for src, name in [("SlashFx/SlashCurved/SpriteSheet.png", "slash_curved.png"), ("Elemental/Flam/SpriteSheet.png", "flame.png"),
                      ("Elemental/Ice/SpriteSheet.png", "ice.png"), ("Elemental/Explosion/SpriteSheet.png", "explosion.png"),
                      ("Smoke/Smoke/SpriteSheet.png", "smoke.png"), ("Magic/Aura/SpriteSheet.png", "aura.png"),
                      ("Magic/Shield/SpriteSheetBlue.png", "shield.png"), ("Magic/Boost/SpriteSheet.png", "boost.png"),
                      ("Particle/LeafPink.png", "leaf_pink.png"), ("Particle/Leaf.png", "leaf.png"), ("Particle/Snow.png", "snow.png"),
                      ("Particle/Fire.png", "ember.png"), ("Particle/Bamboo.png", "bamboo_leaf.png"), ("Particle/Spark.png", "spark.png")]:
        im = Image.open(f"{NA}/FX/{src}").convert("RGBA")
        im.save(os.path.join(ef, name))
    print("effects ok")


# ---------------------------------------------------------------------- audio
MUSIC = {
    "menu": "1 - Adventure Begin.ogg",
    "world1": "35 - Adventure.ogg",
    "world2": "26 - Lost Village.ogg",
    "world3": "19 - Ascension.ogg",
    "world4": "12 - Temple.ogg",
    "world5": "10 - Dark Castle.ogg",
    "world6": "14 - Curse.ogg",
    "boss": "17 - Fight.ogg",
    "boss2": "34  - Fight.ogg",
    "final_boss": "24 - Final Area.ogg",
    "credits": "15 - Credit Theme.ogg",
    "victory": "8 - End Theme.ogg",
}
SFX_NA = {
    "coin": "Bonus/Coin.wav", "gem": "Bonus/Gold1.wav", "powerup": "Bonus/PowerUp1.wav", "bonus": "Bonus/Bonus.wav",
    "jump": "Jump & Bounce/Jump.wav", "bounce": "Jump & Bounce/Bounce.wav", "hit": "Hit & Impact/Hit1.wav",
    "hit2": "Hit & Impact/Hit5.wav", "impact": "Hit & Impact/Impact.wav", "enemy_die": "Hit & Impact/Impact3.wav",
    "explosion": "Elemental/Explosion.wav", "fireball": "Elemental/Fireball.wav", "fire": "Elemental/Fire.wav",
    "heal": "Magic & Skill/Heal.wav", "magic": "Magic & Skill/Magic1.wav", "special": "Magic & Skill/Magic3.wav",
    "spirit": "Magic & Skill/Spirit.wav", "menu_accept": "Menu/Accept.wav", "menu_move": "Menu/Move1.wav",
    "menu_cancel": "Menu/Cancel.wav", "alert": "Alert/Alert2.wav", "water": "Elemental/Water1.wav",
}
JINGLES = {"level_complete": "Success1.wav", "game_over": "GameOver.wav", "unlock": "LevelUp1.wav", "secret": "Secret1.wav",
           "boss_defeat": "Success3.wav"}
SFX_KENNEY = {
    "footstep1": "kenney_rpgaudio/Audio/footstep00.ogg", "footstep2": "kenney_rpgaudio/Audio/footstep02.ogg",
    "footstep3": "kenney_rpgaudio/Audio/footstep04.ogg", "land": "kenney_impactsounds/Audio/footstep_grass_002.ogg",
    "swing1": "kenney_rpgaudio/Audio/knifeSlice.ogg", "swing2": "kenney_rpgaudio/Audio/knifeSlice2.ogg",
    "draw": "kenney_rpgaudio/Audio/drawKnife1.ogg", "sword_hit": "kenney_impactsounds/Audio/impactMetal_medium_002.ogg",
    "chest_open": "kenney_rpgaudio/Audio/doorOpen_1.ogg", "click": "kenney_interfacesounds/Audio/click_002.ogg",
    "pop": "kenney_interfacesounds/Audio/maximize_006.ogg", "error": "kenney_interfacesounds/Audio/error_004.ogg",
    "purchase": "kenney_rpgaudio/Audio/handleCoins2.ogg", "throw": "kenney_rpgaudio/Audio/cloth2.ogg",
    "checkpoint": "kenney_interfacesounds/Audio/confirmation_002.ogg", "boss_fight": "kenney_voiceoverfighter/Audio/fight.ogg",
    "boss_win": "kenney_voiceoverfighter/Audio/you_win.ogg", "ready": "kenney_voiceoverfighter/Audio/ready.ogg",
    "game_over_voice": "kenney_voiceoverfighter/Audio/game_over.ogg", "boss_stomp": "kenney_impactsounds/Audio/impactPlate_heavy_001.ogg",
    "boss_hurt": "kenney_impactsounds/Audio/impactPunch_heavy_002.ogg", "logo": "kenney_musicjingles/Audio/jingles_NES02.ogg",
    "whoosh": "kenney_interfacesounds/Audio/minimize_006.ogg",
}


def build_audio():
    md = mk("audio", "music")
    for key, f in MUSIC.items():
        cp(f"{NA}/Audio/Musics/{f}", md, key + ".ogg")
    sd = mk("audio", "sfx")
    for key, f in SFX_NA.items():
        cp(f"{NA}/Audio/Sounds/{f}", sd, key + ".wav")
    for key, f in JINGLES.items():
        cp(f"{NA}/Audio/Jingles/{f}", sd, key + ".wav")
    missing = []
    for key, f in SFX_KENNEY.items():
        p = f"{KEN}/{f}"
        if os.path.exists(p):
            cp(p, sd, key + ".ogg")
        else:
            missing.append(f)
    print("audio ok; missing kenney:", missing)


if __name__ == "__main__":
    steps = sys.argv[2:] or ["ninja", "tiles", "enemies", "bg", "ui", "fx", "audio"]
    table = {"ninja": build_ninja, "tiles": build_tiles, "enemies": build_enemies, "bg": build_backgrounds,
             "ui": build_ui, "fx": build_effects, "audio": build_audio}
    for s in steps:
        table[s]()


def build_chest():
    im = Image.open(f"{NA}/Items/Treasure/BigTreasureChest.png").convert("RGBA")
    for i, n in enumerate(["chest_closed", "chest_open"]):
        im.crop((i * 16, 0, i * 16 + 16, 14)).resize((64, 56), Image.NEAREST).save(os.path.join(mk("environments", "props"), n + ".png"))


def postprocess_backgrounds():
    import glob
    for f in glob.glob(os.path.join(A, "backgrounds", "background_*.png")):
        im = Image.open(f).convert("RGBA")
        px = im.load()
        w, h = im.size
        key = (255, 255, 255) if "clouds" not in f else (195, 227, 255)
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                d = abs(r - key[0]) + abs(g - key[1]) + abs(b - key[2])
                if d < 6:
                    px[x, y] = (r, g, b, 0)
        im.save(f)
