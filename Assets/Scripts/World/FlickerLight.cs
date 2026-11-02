using UnityEngine;

namespace NightClass
{
    /// <summary>Old fluorescent tube: hums, flickers and sometimes dies for a moment.</summary>
    public class FlickerLight : MonoBehaviour
    {
        public Light lamp;
        public Renderer tube;
        public Color emission = new Color(1.6f, 1.5f, 1.3f);
        public bool broken;
        public bool off;
        float baseIntensity, timer, state = 1f;
        MaterialPropertyBlock mpb;

        void Start()
        {
            if (lamp == null) lamp = GetComponent<Light>();
            if (lamp != null) baseIntensity = lamp.intensity;
            mpb = new MaterialPropertyBlock();
            timer = Random.Range(0.5f, 6f);
        }

        public void Kill()
        {
            off = true;
            Apply(0f);
        }

        void Update()
        {
            if (off) return;
            timer -= Time.deltaTime;
            if (timer <= 0f)
            {
                if (broken)
                {
                    state = state > 0.5f ? 0f : 1f;
                    timer = state > 0.5f ? Random.Range(0.05f, 0.9f) : Random.Range(0.04f, 0.5f);
                }
                else
                {
                    state = Random.value < 0.85f ? 1f : Random.Range(0.1f, 0.6f);
                    timer = state > 0.95f ? Random.Range(2f, 9f) : Random.Range(0.03f, 0.12f);
                }
            }
            float n = 0.94f + 0.06f * Mathf.PerlinNoise(Time.time * 18f, transform.position.x);
            Apply(state * n);
        }

        void Apply(float k)
        {
            if (lamp != null) lamp.intensity = baseIntensity * k;
            if (tube != null)
            {
                tube.GetPropertyBlock(mpb);
                mpb.SetColor("_EmissionColor", emission * k);
                tube.SetPropertyBlock(mpb);
            }
        }
    }
}
