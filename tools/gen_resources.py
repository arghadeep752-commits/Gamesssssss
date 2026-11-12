"""Generates the data .tres resources (characters, weapons, power-ups, skins, 24 levels)."""
import os
import sys

PRJ = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/ninja_shadow_legacy"
R = os.path.join(PRJ, "resources")


def val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, tuple) and len(v) == 4:
        return "Color(%s, %s, %s, %s)" % v
    if isinstance(v, tuple) and len(v) == 2:
        return "Vector2(%s, %s)" % v
    if isinstance(v, list):
        return "PackedStringArray(%s)" % ", ".join('"%s"' % x for x in v)
    if isinstance(v, str) and v.startswith("TEX:"):
        return 'ExtResource("2")'
    return '"%s"' % str(v).replace('"', '\\"')


def write(sub, name, cls, script, props, texture=None):
    d = os.path.join(R, sub)
    os.makedirs(d, exist_ok=True)
    steps = 3 if texture else 2
    lines = ['[gd_resource type="Resource" script_class="%s" load_steps=%d format=3]' % (cls, steps), ""]
    lines.append('[ext_resource type="Script" path="%s" id="1"]' % script)
    if texture:
        lines.append('[ext_resource type="Texture2D" path="%s" id="2"]' % texture)
    lines += ["", "[resource]", 'script = ExtResource("1")']
    for k, v in props.items():
        lines.append("%s = %s" % (k, val(v)))
    with open(os.path.join(d, name + ".tres"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


CS = "res://scripts/core/data/character_data.gd"
characters = [
    ("main_ninja", dict(id="main_ninja", display_name="Kage", description="The last student of the Shadow Clan. Balanced speed, power and agility.",
                        cloth_hue=-1.0, cloth_saturation=1.0, cloth_value=1.0, armor_tint=(1, 1, 1, 1), aura="",
                        max_health=100.0, move_speed=340.0, jump_velocity=960.0, damage_multiplier=1.0, defense=0.0,
                        special_id="kunai_barrage", special_name="Kunai Barrage", special_description="Throws a fan of five kunai.",
                        unlock_type="default", unlock_level=0, price_coins=0, price_gems=0, theme_color=(0.58, 0.32, 0.78, 1))),
    ("shadow_ninja", dict(id="shadow_ninja", display_name="Yoru", description="A shadow-walker. The fastest ninja, but fragile.",
                          cloth_hue=0.74, cloth_saturation=0.45, cloth_value=0.38, armor_tint=(0.62, 0.55, 0.85, 1), aura="shadow",
                          max_health=85.0, move_speed=385.0, jump_velocity=990.0, damage_multiplier=0.95, defense=0.0,
                          special_id="shadow_dash", special_name="Shadow Dash", special_description="Becomes a shadow and dashes through enemies, untouchable.",
                          unlock_type="level", unlock_level=8, price_coins=1800, price_gems=0, theme_color=(0.32, 0.22, 0.48, 1))),
    ("samurai_ninja", dict(id="samurai_ninja", display_name="Raiden", description="Clad in samurai armour. Slow, tough and hits like thunder.",
                           cloth_hue=0.0, cloth_saturation=1.1, cloth_value=0.85, armor_tint=(1.25, 1.05, 0.6, 1), aura="gold",
                           max_health=130.0, move_speed=315.0, jump_velocity=935.0, damage_multiplier=1.3, defense=0.15,
                           special_id="rising_slash", special_name="Rising Thunder", special_description="A huge rising slash that hits every nearby enemy.",
                           unlock_type="coins", unlock_level=0, price_coins=3500, price_gems=0, theme_color=(0.85, 0.2, 0.15, 1))),
    ("fire_ninja", dict(id="fire_ninja", display_name="Homura", description="Trained in the volcano monasteries. Burns everything in her path.",
                        cloth_hue=0.06, cloth_saturation=1.25, cloth_value=1.05, armor_tint=(1.15, 0.78, 0.6, 1), aura="fire",
                        max_health=100.0, move_speed=350.0, jump_velocity=965.0, damage_multiplier=1.1, defense=0.0,
                        special_id="flame_wave", special_name="Flame Wave", special_description="Sends rolling waves of fire both ways along the ground.",
                        unlock_type="level", unlock_level=20, price_coins=0, price_gems=60, theme_color=(1.0, 0.45, 0.1, 1))),
    ("ice_ninja", dict(id="ice_ninja", display_name="Yuki", description="Born in the Frozen Mountains. Controls the battlefield with ice.",
                       cloth_hue=0.53, cloth_saturation=0.85, cloth_value=1.15, armor_tint=(0.8, 0.95, 1.2, 1), aura="ice",
                       max_health=105.0, move_speed=345.0, jump_velocity=975.0, damage_multiplier=1.0, defense=0.05,
                       special_id="frost_nova", special_name="Frost Nova", special_description="Freezes every nearby enemy solid and damages them.",
                       unlock_type="level", unlock_level=12, price_coins=2600, price_gems=0, theme_color=(0.4, 0.8, 1.0, 1))),
]
for name, p in characters:
    write("characters", name, "CharacterData", CS, p)

WS = "res://scripts/core/data/weapon_data.gd"
weapons = [
    ("katana", "res://assets/weapons/icon_katana.png", dict(id="katana", display_name="Katana", description="A balanced blade. Fast, reliable slashes.",
        icon="TEX:", kind="melee", base_damage=20.0, damage_per_level=6.0, max_level=5, attack_cooldown=0.30, attack_speed=1.0, reach=(92, 84),
        hits_per_attack=1, projectile="", projectile_speed=0.0, effect_color=(1, 1, 1, 1), ability_id="dash_slash", ability_name="Dash Slash",
        ability_cooldown=3.0, unlock_type="default", unlock_level=0, price_coins=0, price_gems=0, upgrade_base_cost=300)),
    ("dual_blades", "res://assets/weapons/icon_sai.png", dict(id="dual_blades", display_name="Dual Blades", description="Twin sai. Every attack strikes twice.",
        icon="TEX:", kind="melee", base_damage=13.0, damage_per_level=4.0, max_level=5, attack_cooldown=0.22, attack_speed=1.3, reach=(84, 76),
        hits_per_attack=2, projectile="", projectile_speed=0.0, effect_color=(0.7, 0.95, 1, 1), ability_id="whirlwind", ability_name="Whirlwind",
        ability_cooldown=4.0, unlock_type="level", unlock_level=6, price_coins=1200, price_gems=0, upgrade_base_cost=320)),
    ("shuriken", "res://assets/weapons/icon_shuriken.png", dict(id="shuriken", display_name="Shuriken", description="Throwing stars that fly straight across the screen.",
        icon="TEX:", kind="ranged", base_damage=14.0, damage_per_level=4.0, max_level=5, attack_cooldown=0.34, attack_speed=1.1, reach=(0, 0),
        hits_per_attack=1, projectile="shuriken", projectile_speed=980.0, effect_color=(0.85, 0.9, 1, 1), ability_id="fan_throw", ability_name="Star Fan",
        ability_cooldown=3.0, unlock_type="level", unlock_level=10, price_coins=1500, price_gems=0, upgrade_base_cost=340)),
    ("bow", "res://assets/weapons/icon_bow.png", dict(id="bow", display_name="Bow", description="Slow but powerful long-range arrows.",
        icon="TEX:", kind="ranged", base_damage=26.0, damage_per_level=7.0, max_level=5, attack_cooldown=0.55, attack_speed=1.0, reach=(0, 0),
        hits_per_attack=1, projectile="arrow", projectile_speed=1300.0, effect_color=(1, 0.95, 0.7, 1), ability_id="power_shot", ability_name="Piercing Shot",
        ability_cooldown=3.5, unlock_type="level", unlock_level=14, price_coins=2500, price_gems=0, upgrade_base_cost=380)),
    ("dragon_blade", "res://assets/weapons/icon_bigsword.png", dict(id="dragon_blade", display_name="Dragon Blade", description="Legendary blade forged in dragon fire. Every swing burns.",
        icon="TEX:", kind="melee", base_damage=34.0, damage_per_level=8.0, max_level=5, attack_cooldown=0.34, attack_speed=0.95, reach=(112, 92),
        hits_per_attack=1, projectile="", projectile_speed=0.0, effect_color=(1, 0.55, 0.15, 1), ability_id="flame_wave", ability_name="Dragon Fire",
        ability_cooldown=4.5, unlock_type="level", unlock_level=18, price_coins=0, price_gems=45, upgrade_base_cost=500)),
]
for name, tex, p in weapons:
    write("weapons", name, "WeaponData", WS, p, tex)

PS = "res://scripts/core/data/powerup_data.gd"
powerups = [
    ("double_jump", "res://assets/ui/icons/icon_jump.png", dict(id="double_jump", display_name="Double Jump", description="Jump again in mid-air.",
        icon="TEX:", color=(0.5, 0.9, 1, 1), duration=20.0, magnitude=1.0, shop_price_coins=150, shop_price_gems=0)),
    ("shield", "res://assets/ui/icons/icon_shield.png", dict(id="shield", display_name="Shield", description="Blocks all damage for a short time.",
        icon="TEX:", color=(0.45, 0.75, 1, 1), duration=10.0, magnitude=1.0, shop_price_coins=200, shop_price_gems=0)),
    ("speed_boost", "res://assets/ui/icons/icon_arrow.png", dict(id="speed_boost", display_name="Speed Boost", description="Run much faster.",
        icon="TEX:", color=(1, 0.95, 0.4, 1), duration=8.0, magnitude=1.45, shop_price_coins=150, shop_price_gems=0)),
    ("health_recovery", "res://assets/ui/hud/hud_heart.png", dict(id="health_recovery", display_name="Health Recovery", description="Restores 40 health instantly.",
        icon="TEX:", color=(1, 0.35, 0.4, 1), duration=0.0, magnitude=40.0, shop_price_coins=120, shop_price_gems=0)),
    ("critical_strike", "res://assets/ui/icons/icon_target.png", dict(id="critical_strike", display_name="Critical Strike", description="Every hit is a critical hit for double damage.",
        icon="TEX:", color=(1, 0.4, 0.2, 1), duration=10.0, magnitude=2.0, shop_price_coins=250, shop_price_gems=0)),
    ("energy_boost", "res://assets/ui/icons/icon_burst.png", dict(id="energy_boost", display_name="Special Energy", description="Fills your special energy instantly.",
        icon="TEX:", color=(0.75, 0.5, 1, 1), duration=0.0, magnitude=100.0, shop_price_coins=180, shop_price_gems=0)),
]
for name, tex, p in powerups:
    write("powerups", name, "PowerupData", PS, p, tex)

SS = "res://scripts/core/data/skin_data.gd"
skins = [
    ("original", dict(id="original", display_name="Original", cloth_hue=-1.0, cloth_saturation=1.0, cloth_value=1.0, armor_tint=(1, 1, 1, 1), price_coins=0, price_gems=0)),
    ("crimson", dict(id="crimson", display_name="Crimson", cloth_hue=0.985, cloth_saturation=1.15, cloth_value=0.85, armor_tint=(1, 0.9, 0.85, 1), price_coins=800, price_gems=0)),
    ("jade", dict(id="jade", display_name="Jade", cloth_hue=0.38, cloth_saturation=0.9, cloth_value=0.95, armor_tint=(0.9, 1.05, 0.95, 1), price_coins=900, price_gems=0)),
    ("midnight", dict(id="midnight", display_name="Midnight", cloth_hue=0.62, cloth_saturation=0.65, cloth_value=0.45, armor_tint=(0.7, 0.75, 0.95, 1), price_coins=1200, price_gems=0)),
    ("royal_gold", dict(id="royal_gold", display_name="Royal Gold", cloth_hue=0.12, cloth_saturation=0.95, cloth_value=1.15, armor_tint=(1.3, 1.1, 0.55, 1), price_coins=0, price_gems=20)),
    ("sakura", dict(id="sakura", display_name="Sakura", cloth_hue=0.92, cloth_saturation=0.5, cloth_value=1.3, armor_tint=(1.1, 0.95, 1.0, 1), price_coins=0, price_gems=15)),
]
for name, p in skins:
    write("skins", name, "SkinData", SS, p)

LS = "res://scripts/core/data/level_data.gd"
W_POOLS = {
    1: ["a:slime,snail", "b:bee", "c:ninja", "d:frog"],
    2: ["a:mouse,ladybug", "b:fly", "c:ninja,kunai_ninja", "d:frog"],
    3: ["a:block_slime,snail", "b:bee", "c:ninja,kunai_ninja", "d:frog"],
    4: ["a:spike_slime,ring_worm", "b:fly", "c:kunai_ninja,elite_ninja", "d:frog"],
    5: ["a:fire_slime,ring_worm", "b:bee", "c:elite_ninja,kunai_ninja", "d:frog"],
    6: ["a:spike_slime,block_slime", "b:fly,bee", "c:elite_ninja,kunai_ninja,ninja", "d:frog"],
}
BOSSES = {1: "shadow_samurai", 2: "demon_ronin", 3: "ice_guardian", 4: "temple_beast", 5: "fire_lord", 6: "shadow_king"}
LEVELS = [
    ("The Forgotten Path", ["start_tutorial", "flat_coins", "gap_small", "crates", "checkpoint", "steps_up", "coin_blocks", "hill", "goal"]),
    ("Bamboo Crossing", ["start", "platforms_low", "gap_small", "canopy", "checkpoint_heart", "pit_platforms", "crates", "secret_room", "goal"]),
    ("Hidden Waterfall", ["start", "steps_up", "fish_pond", "treasure_ledge", "checkpoint", "moving_gap", "ladder_tower", "spring_jump", "flat_coins", "goal"]),
    ("Samurai's Trial", ["start", "enemy_camp", "gap_spikes", "checkpoint_heart", "ninja_dojo", "platforms_low", "arena"]),
    ("Silent Streets", ["start", "flat_coins", "crates", "enemy_camp", "checkpoint", "high_road", "coin_blocks", "tunnel", "goal"]),
    ("Broken Bridge", ["start", "falling_bridge", "platforms_low", "chomper_bridge", "checkpoint_heart", "pit_platforms", "double_up", "moving_gap", "goal"]),
    ("Abandoned Shrine", ["start", "ninja_dojo", "ladder_tower", "secret_room", "checkpoint", "spike_corridor", "vertical_climb", "treasure_ledge", "goal"]),
    ("Demon Gate", ["start", "enemy_camp", "saw_run", "checkpoint_heart", "high_road", "gap_spikes", "arena"]),
    ("Frozen Trail", ["start", "hill", "gap_small", "canopy", "checkpoint", "spring_jump", "flat_coins", "steps_up", "goal"]),
    ("Ice Cavern", ["start", "tunnel", "crusher_hall", "fish_pond", "checkpoint_heart", "coin_blocks", "vertical_climb", "secret_room", "goal"]),
    ("Frozen Bridge", ["start", "falling_bridge", "pit_platforms", "checkpoint", "moving_gap", "chomper_bridge", "shadow_void", "double_up", "goal"]),
    ("Guardian's Peak", ["start", "vertical_climb", "enemy_camp", "checkpoint_heart", "ladder_tower", "high_road", "arena"]),
    ("Temple Entrance", ["start", "steps_up", "spike_corridor", "crusher_hall", "checkpoint", "treasure_ledge", "saw_run", "crates", "goal"]),
    ("Ancient Hall", ["start", "tunnel", "ninja_dojo", "checkpoint_heart", "crusher_hall", "secret_room", "coin_blocks", "gap_spikes", "goal"]),
    ("Cursed Chamber", ["start", "ladder_tower", "spike_corridor", "checkpoint", "chomper_bridge", "vertical_climb", "enemy_camp", "crusher_hall", "goal"]),
    ("Sacred Battlefield", ["start", "enemy_camp", "gap_spikes", "checkpoint_heart", "ninja_dojo", "saw_run", "arena"]),
    ("Ashen Road", ["start", "lava_steps", "flat_coins", "checkpoint", "gap_spikes", "hill", "lava_moving", "enemy_camp", "goal"]),
    ("Burning Village", ["start", "crates", "lava_moving", "checkpoint_heart", "high_road", "fish_pond", "coin_blocks", "spike_corridor", "goal"]),
    ("Fortress Wall", ["start", "ladder_tower", "crusher_hall", "checkpoint", "vertical_climb", "lava_steps", "secret_room", "saw_run", "goal"]),
    ("Throne Entrance", ["start", "ninja_dojo", "lava_moving", "checkpoint_heart", "enemy_camp", "spike_corridor", "arena"]),
    ("Shadow Path", ["start", "shadow_void", "flat_coins", "checkpoint", "high_road", "falling_bridge", "double_up", "enemy_camp", "goal"]),
    ("Lost Dimension", ["start", "vertical_climb", "shadow_void", "checkpoint_heart", "pit_platforms", "moving_gap", "canopy", "secret_room", "goal"]),
    ("Dark Citadel", ["start", "crusher_hall", "ninja_dojo", "checkpoint", "lava_steps", "spike_corridor", "ladder_tower", "saw_run", "enemy_camp", "goal"]),
    ("Final Destination", ["start", "enemy_camp", "shadow_void", "checkpoint_heart", "ninja_dojo", "lava_moving", "checkpoint", "high_road", "arena"]),
]
OBJECTIVES = {True: "Defeat the boss guarding the gate", False: "Reach the exit gate"}
for i, (name, chunks) in enumerate(LEVELS, start=1):
    world = (i - 1) // 4 + 1
    boss = BOSSES[world] if i % 4 == 0 else ""
    write("levels", "level_%02d" % i, "LevelData", LS, dict(
        index=i, world=world, display_name=name, chunks=chunks, difficulty=round(1.0 + (i - 1) * 0.11, 2),
        enemy_pool=W_POOLS[world], boss_id=boss, par_time=90.0 + len(chunks) * 12.0, objective=OBJECTIVES[bool(boss)]))
print("resources written")
