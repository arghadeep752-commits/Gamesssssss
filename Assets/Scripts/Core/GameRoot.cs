using UnityEngine;

namespace GridProto
{
    /// <summary>
    /// Scene entry point: full native resolution, 60 FPS, graphics quality and ambient light.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class GameRoot : MonoBehaviour
    {
        public PlayerController player;
        public Camera playerCamera;
        public Light sun;
        public ReflectionProbe reflectionProbe;
        public AudioSource ambience;
        public Door door;
        public Hud hud;

        public Color ambientSky = new Color(0.66f, 0.73f, 0.82f);
        public Color ambientEquator = new Color(0.56f, 0.58f, 0.61f);
        public Color ambientGround = new Color(0.38f, 0.37f, 0.35f);

        public static GameRoot Instance { get; private set; }

        void Awake()
        {
            Instance = this;
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            Screen.fullScreen = true;
            Input.multiTouchEnabled = true;
            UseNativeResolution();

            // trilight ambient needs no baked lighting data, so it looks the same in every build
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = ambientSky;
            RenderSettings.ambientEquatorColor = ambientEquator;
            RenderSettings.ambientGroundColor = ambientGround;

            GameSettings.Load();
            ApplyGraphics();
        }

        void Start()
        {
            if (reflectionProbe != null) reflectionProbe.RenderProbe();
            if (ambience != null)
            {
                ambience.clip = ProtoAudio.Wind;
                ambience.loop = true;
                ambience.Play();
            }
#if PROTO_AUTOTEST
            gameObject.AddComponent<AutoTest>();
#endif
        }

        /// <summary>Renders at the phone's full native resolution, never a scaled-down buffer.</summary>
        public static void UseNativeResolution()
        {
            int sw = Display.main.systemWidth;
            int sh = Display.main.systemHeight;
            if (sw <= 0 || sh <= 0) return;
            int w = Mathf.Max(sw, sh);   // the game is landscape only
            int h = Mathf.Min(sw, sh);
            long current = (long)Screen.width * Screen.height;
            long native = (long)w * h;
            if (current < native * 97 / 100)
            {
                Screen.SetResolution(w, h, FullScreenMode.FullScreenWindow);
                Debug.Log("[GridProto] render resolution raised to native " + w + "x" + h);
            }
        }

        public void ApplyGraphics()
        {
            bool high = GameSettings.HighQuality;
            QualitySettings.antiAliasing = high ? 4 : 2;
            QualitySettings.shadows = UnityEngine.ShadowQuality.All;
            QualitySettings.shadowResolution = high ? UnityEngine.ShadowResolution.High : UnityEngine.ShadowResolution.Medium;
            QualitySettings.shadowDistance = high ? 45f : 28f;
            QualitySettings.shadowCascades = 1;
            QualitySettings.shadowProjection = ShadowProjection.StableFit;
            QualitySettings.pixelLightCount = 2;
            QualitySettings.anisotropicFiltering = AnisotropicFiltering.ForceEnable;
            QualitySettings.realtimeReflectionProbes = true;
            QualitySettings.lodBias = 2f;
            if (sun != null) sun.shadows = high ? LightShadows.Soft : LightShadows.Hard;
        }
    }
}
