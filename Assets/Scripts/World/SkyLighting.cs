using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS
{
    /// <summary>
    /// The scene's atmosphere. Two looks, switchable in Settings:
    ///
    ///  - Night fog (default), in the style of classic mobile horror games: no sky, a near-black
    ///    exponential fog that swallows everything beyond ~40 m, an even, fairly bright ambient
    ///    light so nearby things stay readable, a dim cool moon and a short draw distance (which
    ///    also makes the game much cheaper to render).
    ///  - Day: the HDRI sky with the ambient light baked from it (spherical harmonics), the sun
    ///    and light haze.
    ///
    /// Lighting is not baked by the editor, so this is what lights the shadows.
    /// </summary>
    public class SkyLighting : MonoBehaviour
    {
        public static SkyLighting I { get; private set; }

        [Header("Day (HDRI sky)")]
        public float[] sh = new float[27];
        public Color fogColor = new Color(0.72f, 0.76f, 0.83f);
        public float fogDensity = 0.0024f;
        public float ambientBoost = 1f;
        public Material skybox;
        public Color sunColor = Color.white;
        public float sunIntensity = 1.6f;
        public float dayFarClip = 1800f;

        [Header("Night fog")]
        public Color nightFogColor = new Color(0.012f, 0.014f, 0.02f);
        public float nightFogDensity = 0.05f;
        public Color nightAmbient = new Color(0.56f, 0.6f, 0.68f);
        public Color nightSkyTint = new Color(0.1f, 0.12f, 0.18f);
        public Color moonColor = new Color(0.72f, 0.8f, 1f);
        public float moonIntensity = 0.45f;
        public float nightFarClip = 95f;

        [Header("Scene objects")]
        public Light sun;
        public Camera cam;
        public Material water;
        public GameObject farMountains;
        public Lantern[] lanterns;

        public bool Night { get; private set; }
        Quaternion dayRotation;
        float dayReflect = -1f, daySunStrength = -1f;
        float[] lanternBase;

        void Awake()
        {
            I = this;
            if (sun != null) dayRotation = sun.transform.rotation;
            if (water != null)
            {
                if (water.HasProperty("_ReflectStrength")) dayReflect = water.GetFloat("_ReflectStrength");
                if (water.HasProperty("_SunStrength")) daySunStrength = water.GetFloat("_SunStrength");
            }
            if (lanterns != null)
            {
                lanternBase = new float[lanterns.Length];
                for (int i = 0; i < lanterns.Length; i++) lanternBase[i] = lanterns[i] != null ? lanterns[i].baseGlowSize : 1.3f;
            }
            Apply(GameSettings.NightStyle);
        }

        public void Apply(bool night)
        {
            Night = night;
            var probe = new SphericalHarmonicsL2();
            if (night)
            {
                // even light from all around, a little brighter from above
                probe.AddAmbientLight(nightAmbient);
                probe.AddDirectionalLight(Vector3.up, nightSkyTint, 0.6f);
            }
            else if (sh != null && sh.Length >= 27)
            {
                for (int c = 0; c < 3; c++)
                    for (int i = 0; i < 9; i++)
                        probe[c, i] = sh[c * 9 + i] * ambientBoost;
            }
            RenderSettings.ambientMode = AmbientMode.Skybox;
            RenderSettings.ambientProbe = probe;
            RenderSettings.ambientIntensity = 1f;
            RenderSettings.skybox = night ? null : skybox;
            RenderSettings.reflectionIntensity = night ? 0.12f : 1f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogColor = night ? nightFogColor : fogColor;
            RenderSettings.fogDensity = night ? nightFogDensity : fogDensity;

            if (sun != null)
            {
                sun.color = night ? moonColor : sunColor;
                sun.intensity = night ? moonIntensity : sunIntensity;
                // a higher moon keeps shadows short and readable
                sun.transform.rotation = night ? Quaternion.Euler(62f, dayRotation.eulerAngles.y + 40f, 0f) : dayRotation;
            }
            if (cam != null)
            {
                cam.clearFlags = night ? CameraClearFlags.SolidColor : CameraClearFlags.Skybox;
                cam.backgroundColor = nightFogColor;
                cam.farClipPlane = night ? nightFarClip : dayFarClip;
            }
            if (water != null)
            {
                if (dayReflect >= 0f) water.SetFloat("_ReflectStrength", night ? 0.16f : dayReflect);
                if (daySunStrength >= 0f) water.SetFloat("_SunStrength", night ? daySunStrength * 0.35f : daySunStrength);
            }
            if (farMountains != null) farMountains.SetActive(!night);
            if (lanterns != null && lanternBase != null)
                for (int i = 0; i < lanterns.Length; i++)
                    if (lanterns[i] != null) lanterns[i].baseGlowSize = lanternBase[i] * (night ? 1.9f : 1f);
        }
    }
}
