using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace NightClass
{
    /// <summary>
    /// Applies the graphics profile: URP quality level (MSAA / shadows / render scale) and which
    /// post effects run. Low keeps the Galaxy A21s class of phones smooth.
    /// </summary>
    public class QualityManager : MonoBehaviour
    {
        public static QualityManager I { get; private set; }
        public Volume volume;

        void Awake() { I = this; }

        public void Apply()
        {
            int lvl = Mathf.Clamp((int)GameSettings.Graphics, 0, 2);
            if (QualitySettings.names.Length > lvl) QualitySettings.SetQualityLevel(lvl, true);
            var urp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (urp != null)
            {
                float shortSide = Mathf.Min(Screen.width, Screen.height);
                float maxShort = lvl == 0 ? 720f : (lvl == 1 ? 900f : 1080f);
                float scale = Mathf.Clamp(maxShort / Mathf.Max(1f, shortSide), 0.6f, 1f);
                if (lvl == 0) scale = Mathf.Min(scale, 0.85f);
                urp.renderScale = scale;
            }
            if (volume != null && volume.profile != null)
            {
                VolumeProfile p = volume.profile;
                Bloom bloom;
                if (p.TryGet(out bloom)) bloom.active = lvl >= 1;
                FilmGrain grain;
                if (p.TryGet(out grain)) grain.active = lvl >= 1;
                ChromaticAberration ca;
                if (p.TryGet(out ca)) ca.active = lvl >= 2;
            }
            GameSettings.Apply();
            Debug.Log("[RF] quality " + lvl + " (" + (lvl < QualitySettings.names.Length ? QualitySettings.names[lvl] : "?") + ") gpu=" + SystemInfo.graphicsDeviceName +
                      " mem=" + SystemInfo.systemMemorySize + " scale=" + (urp != null ? urp.renderScale.ToString("0.00") : "-"));
        }
    }
}
