using UnityEngine;

namespace ZombieStrike
{
    /// <summary>Fire-light flicker.</summary>
    public class Flicker : MonoBehaviour
    {
        Light lightSource;
        float baseIntensity;
        float seed;

        void Start()
        {
            lightSource = GetComponent<Light>();
            baseIntensity = lightSource != null ? lightSource.intensity : 1f;
            seed = Random.value * 100f;
        }

        void Update()
        {
            if (lightSource == null) return;
            float t = Time.time * 9f + seed;
            float n = Mathf.PerlinNoise(t, seed) * 0.6f + Mathf.PerlinNoise(t * 2.3f, seed + 7f) * 0.4f;
            lightSource.intensity = baseIntensity * (0.7f + n * 0.6f);
        }
    }
}
