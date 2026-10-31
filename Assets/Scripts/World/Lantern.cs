using UnityEngine;

namespace RealFPS
{
    /// <summary>A collectible lantern with a flickering glow.</summary>
    public class Lantern : MonoBehaviour
    {
        public Transform glow;
        public Transform flame;
        public float baseGlowSize = 1.4f;

        public bool Collected { get; private set; }
        float seed;
        float collectT;
        Vector3 startScale;
        Vector3 startPos;

        void Start()
        {
            seed = Random.value * 100f;
            startScale = transform.localScale;
            startPos = transform.position;
        }

        public void Collect()
        {
            if (Collected) return;
            Collected = true;
            collectT = 0f;
            if (Game.I != null) Game.I.OnLanternFound(this);
        }

        void Update()
        {
            float t = Time.time + seed;
            float flicker = 0.85f + 0.1f * Mathf.Sin(t * 13.7f) + 0.06f * Mathf.Sin(t * 23.1f + 1.3f) + 0.05f * Mathf.PerlinNoise(t * 3f, seed);
            if (!Collected)
            {
                if (glow != null) glow.localScale = Vector3.one * baseGlowSize * flicker;
                if (flame != null) flame.localScale = new Vector3(1f, 0.85f + 0.3f * flicker, 1f) * 0.12f;
                return;
            }
            collectT += Time.deltaTime;
            float k = Mathf.Clamp01(collectT / 0.7f);
            transform.position = startPos + Vector3.up * (k * k * 0.8f);
            transform.localScale = startScale * (1f - k);
            if (glow != null) glow.localScale = Vector3.one * baseGlowSize * (1f + k * 2.5f) * (1f - k);
            if (k >= 1f) gameObject.SetActive(false);
        }
    }
}
