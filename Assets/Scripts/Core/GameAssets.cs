using UnityEngine;

namespace NightClass
{
    public enum Surface { Concrete, Wood, Tile, Metal }

    /// <summary>
    /// Every asset the runtime needs. The editor build script fills the fields,
    /// so nothing is loaded by name at runtime. Missing assets fall back gracefully.
    /// </summary>
    public class GameAssets : MonoBehaviour
    {
        public static GameAssets I { get; private set; }

        [Header("Fonts")]
        public Font uiFont;
        public Font uiFontBold;
        public Font titleFont;
        public Font chalkFont;

        [Header("UI sprites")]
        public Sprite circle, ring, rounded, glow, vignette, dot;
        public Sprite iconHand, iconDrop, iconCrouch, iconStand, iconHide, iconUnhide, iconFire, iconJump, iconPause;
        public Sprite itemMainKey, itemHammer, itemTorch, itemNote, itemSafeKey, itemSpring, itemDynamite;

        [Header("Audio")]
        public AudioClip uiClick, pickup, drop, doorOpen, doorClose, doorLocked, plankBreak;
        public AudioClip fireWhoosh, fireLoop, water, steam, keypadBeep, keypadOk, keypadNo, safeOpen;
        public AudioClip explosion, fuse, eat, bell, motor, trapdoor, burnScream, scream, heartbeat;
        public AudioClip chaseLoop, ambientLoop, teacherHum, jump, land, rulerHit, lightPop, musicBox, slam;
        public AudioClip[] stepConcrete, stepWood, stepTile, stepMetal, teacherSteps, ambientOneShots;

        [Header("Effects")]
        public Material fireMat, smokeMat, waterMat, sparkMat, dustMat;

        [Header("Atmosphere")]
        public Color fogColor = new Color(0.035f, 0.045f, 0.06f);
        public float fogDensity = 0.03f;
        public float fogDensityHard = 0.075f;

        void Awake()
        {
            I = this;
            if (uiFont == null) uiFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (uiFontBold == null) uiFontBold = uiFont;
            if (titleFont == null) titleFont = uiFontBold;
            if (chalkFont == null) chalkFont = uiFontBold;
        }

        public AudioClip[] StepsFor(Surface s)
        {
            switch (s)
            {
                case Surface.Wood: return stepWood;
                case Surface.Tile: return stepTile;
                case Surface.Metal: return stepMetal;
                default: return stepConcrete;
            }
        }

        public Sprite IconFor(ItemType t)
        {
            switch (t)
            {
                case ItemType.MainKey: return itemMainKey;
                case ItemType.Hammer: return itemHammer;
                case ItemType.Torch: return itemTorch;
                case ItemType.CodeNote: return itemNote;
                case ItemType.SafeKey: return itemSafeKey;
                case ItemType.Spring: return itemSpring;
                case ItemType.Dynamite: return itemDynamite;
            }
            return null;
        }
    }
}
