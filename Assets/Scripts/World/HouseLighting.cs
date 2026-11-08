using UnityEngine;
using UnityEngine.Rendering;

namespace GridProto
{
    /// <summary>
    /// Runtime lighting for the baked house: renders the room reflection probes once at start, adapts the
    /// camera exposure to the baked light around the player (eyes adjust walking in and out of the house),
    /// and lights the enemy from the baked probe grid so he matches the room he is in.
    /// </summary>
    public class HouseLighting : MonoBehaviour
    {
        public HouseData data;
        public Transform viewer;
        public Renderer[] dynamicRenderers;
        public ReflectionProbe[] probes;
        public float key = 0.5f;
        public float minExposure = 0.85f;
        public float maxExposure = 6.5f;
        public float probeExposure = 3.2f;
        public float shScale = 0.72f;

        static readonly int ExposureId = Shader.PropertyToID("_HouseExposure");
        static readonly int ProbeExposureId = Shader.PropertyToID("_HouseProbeExposure");
        readonly Color[] cols = new Color[6];
        readonly SphericalHarmonicsL2[] sh = new SphericalHarmonicsL2[1];
        MaterialPropertyBlock block;
        float exposure = 1.6f;
        int probeIndex;
        int pendingId = -1;
        bool probesDone;

        public float Exposure { get { return exposure; } }
        public bool ProbesDone { get { return probesDone; } }

        void Awake()
        {
            block = new MaterialPropertyBlock();
            Shader.SetGlobalFloat(ProbeExposureId, probeExposure);
            if (viewer != null && data != null) exposure = TargetExposure(viewer.position);
            Shader.SetGlobalFloat(ExposureId, probeExposure);
            if (dynamicRenderers != null)
                foreach (Renderer r in dynamicRenderers) if (r != null) r.lightProbeUsage = LightProbeUsage.CustomProvided;
        }

        void Update()
        {
            // reflection probes: one at a time, rendered with a fixed exposure, then auto exposure takes over
            if (!probesDone)
            {
                Shader.SetGlobalFloat(ExposureId, probeExposure);
                if (probes == null || probes.Length == 0) { probesDone = true; }
                else if (pendingId < 0 || probes[probeIndex].IsFinishedRendering(pendingId))
                {
                    if (pendingId >= 0) probeIndex++;
                    if (probeIndex >= probes.Length) probesDone = true;
                    else pendingId = probes[probeIndex].RenderProbe();
                }
                if (!probesDone) return;
            }
            float dt = Mathf.Min(Time.unscaledDeltaTime, 0.1f);
            if (viewer != null && data != null)
            {
                float target = TargetExposure(viewer.position);
                float speed = target > exposure ? 1.6f : 2.6f;    // eyes adapt to bright light faster
                exposure = Mathf.Lerp(exposure, target, 1f - Mathf.Exp(-dt * speed));
            }
            Shader.SetGlobalFloat(ExposureId, exposure);
        }

        void LateUpdate()
        {
            if (data == null || dynamicRenderers == null) return;
            foreach (Renderer r in dynamicRenderers)
            {
                if (r == null || !r.enabled) continue;
                data.Sample(r.bounds.center, cols);
                sh[0].Clear();
                float s = shScale * (probesDone ? exposure : probeExposure);
                for (int k = 0; k < 6; k++)
                    sh[0].AddDirectionalLight(HouseData.Dir(k), cols[k] * s, 1f);
                r.GetPropertyBlock(block);
                block.CopySHCoefficientArraysFrom(sh);
                r.SetPropertyBlock(block);
            }
        }

        float TargetExposure(Vector3 p)
        {
            data.Sample(p, cols);
            float lum = 0f;
            for (int k = 0; k < 6; k++) lum += cols[k].r * 0.3f + cols[k].g * 0.59f + cols[k].b * 0.11f;
            lum /= 6f;
            return Mathf.Clamp(key / Mathf.Max(lum, 0.02f), minExposure, maxExposure);
        }
    }
}
