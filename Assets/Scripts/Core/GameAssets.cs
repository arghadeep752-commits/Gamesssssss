using UnityEngine;

namespace RealFPS
{
    /// <summary>
    /// Holds every asset the runtime code needs. The editor build script fills the
    /// fields, so nothing is loaded by name at runtime.
    /// </summary>
    public class GameAssets : MonoBehaviour
    {
        public static GameAssets I { get; private set; }

        [Header("UI")]
        public Font uiFont;
        public Font uiFontBold;
        public Font titleFont;
        public Sprite circle, ring, rounded, glow, dot, fadeH, fadeV;
        public Sprite iconJump, iconCrouch, iconRun, iconPause, iconHand, iconLantern, iconGear;

        [Header("Audio")]
        public AudioClip wind;
        public AudioClip lake;
        public AudioClip fire;
        public AudioClip jump, land, uiClick, pickup, complete;
        public AudioClip[] birds;
        public AudioClip[] stepGrass, stepDirt, stepRock, stepWood, stepWater;

        [Header("Rendering")]
        public Shader postShader;
        public Material grassMaterial;
        public Mesh[] grassMeshes;
        /// <summary>Ambient light (spherical harmonics, 3 x 9 floats) baked from the HDRI sky.</summary>
        public float[] ambientSH = new float[27];
        public Color fogColor = new Color(0.7f, 0.75f, 0.8f);
        public float fogDensity = 0.0024f;

        void Awake()
        {
            I = this;
            if (uiFont == null) uiFont = Resources.GetBuiltinResource<Font>("Arial.ttf");
            if (uiFontBold == null) uiFontBold = uiFont;
            if (titleFont == null) titleFont = uiFontBold;
        }

        public AudioClip[] StepsFor(Surface s)
        {
            switch (s)
            {
                case Surface.Dirt: return stepDirt;
                case Surface.Rock: return stepRock;
                case Surface.Wood: return stepWood;
                case Surface.Water: return stepWater;
                default: return stepGrass;
            }
        }
    }

    public enum Surface { Grass, Dirt, Rock, Wood, Water }
}
