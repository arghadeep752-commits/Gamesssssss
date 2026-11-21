using UnityEngine;

namespace TradersMadness
{
    /// <summary>Makes a UI element jump sideways now and then, like a bad video signal (the title's coloured ghosts).</summary>
    public class Glitch : MonoBehaviour
    {
        public float amount = 5f;
        RectTransform rt;
        Vector2 home;
        float t, burst;

        void Start()
        {
            rt = (RectTransform)transform;
            home = rt.anchoredPosition;
        }

        void Update()
        {
            t -= Time.unscaledDeltaTime;
            if (t <= 0f)
            {
                t = Random.Range(0.06f, 0.18f);
                burst = Random.value < 0.12f ? Random.Range(2f, 4f) : 1f;
            }
            float j = Mathf.Sin(Time.unscaledTime * 31f) * 0.5f + Mathf.Sin(Time.unscaledTime * 7f) * 0.5f;
            rt.anchoredPosition = home + new Vector2(amount * j * burst, (burst > 1f ? Random.Range(-2f, 2f) : 0f));
        }
    }
}
