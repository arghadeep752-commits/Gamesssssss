using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS
{
    /// <summary>
    /// Applies the ambient light baked from the HDRI sky (spherical harmonics),
    /// the fog and the reflection settings when the scene starts. Lighting is
    /// not baked by the editor, so this is what lights the shadows.
    /// </summary>
    public class SkyLighting : MonoBehaviour
    {
        public float[] sh = new float[27];
        public Color fogColor = new Color(0.72f, 0.76f, 0.83f);
        public float fogDensity = 0.0024f;
        public float ambientBoost = 1f;

        void Awake()
        {
            Apply();
        }

        public void Apply()
        {
            if (sh == null || sh.Length < 27) return;
            var probe = new SphericalHarmonicsL2();
            for (int c = 0; c < 3; c++)
                for (int i = 0; i < 9; i++)
                    probe[c, i] = sh[c * 9 + i] * ambientBoost;
            RenderSettings.ambientMode = AmbientMode.Skybox;
            RenderSettings.ambientProbe = probe;
            RenderSettings.ambientIntensity = 1f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogColor = fogColor;
            RenderSettings.fogDensity = fogDensity;
        }
    }
}
