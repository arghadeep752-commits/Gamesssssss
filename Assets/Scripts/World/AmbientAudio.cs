using UnityEngine;

namespace RealFPS
{
    /// <summary>Wind, birds in the trees and water lapping at the nearest lake shore.</summary>
    public class AmbientAudio : MonoBehaviour
    {
        public Vector2 lakeCenter;
        public Vector2 lakeRadii = new Vector2(70f, 45f);
        public float lakeAngle;        // degrees, rotation of the lake ellipse
        public float waterLevel = 21f;

        AudioSource wind, lake;
        float nextBird;

        void Start()
        {
            GameAssets A = GameAssets.I;
            wind = gameObject.AddComponent<AudioSource>();
            wind.clip = A.wind;
            wind.loop = true;
            wind.spatialBlend = 0f;
            wind.volume = 0.32f;
            wind.Play();

            var lg = new GameObject("LakeAudio");
            lg.transform.SetParent(transform, false);
            lake = lg.AddComponent<AudioSource>();
            lake.clip = A.lake;
            lake.loop = true;
            lake.spatialBlend = 1f;
            lake.rolloffMode = AudioRolloffMode.Linear;
            lake.minDistance = 3f;
            lake.maxDistance = 38f;
            lake.dopplerLevel = 0f;
            lake.volume = 0.55f;
            lake.Play();
            nextBird = Time.time + 2f;
        }

        void Update()
        {
            Camera cam = Camera.main;
            if (cam == null) return;
            Vector3 p = cam.transform.position;

            // wind swells a little
            wind.volume = 0.26f + 0.08f * Mathf.PerlinNoise(Time.time * 0.07f, 3.1f);

            // nearest point on the lake ellipse
            float a = lakeAngle * Mathf.Deg2Rad;
            Vector2 d = new Vector2(p.x, p.z) - lakeCenter;
            Vector2 local = new Vector2(d.x * Mathf.Cos(a) + d.y * Mathf.Sin(a), -d.x * Mathf.Sin(a) + d.y * Mathf.Cos(a));
            Vector2 n = new Vector2(local.x / lakeRadii.x, local.y / lakeRadii.y);
            float len = n.magnitude;
            Vector2 onEdge = len > 1e-4f ? new Vector2(n.x / len * lakeRadii.x, n.y / len * lakeRadii.y) : new Vector2(lakeRadii.x, 0f);
            if (len < 1f) onEdge = local; // inside (on the pier): the sound is right here
            Vector2 world = lakeCenter + new Vector2(onEdge.x * Mathf.Cos(a) - onEdge.y * Mathf.Sin(a), onEdge.x * Mathf.Sin(a) + onEdge.y * Mathf.Cos(a));
            lake.transform.position = new Vector3(world.x, waterLevel + 0.2f, world.y);

            // birds in the trees around the listener
            if (Time.time > nextBird && GameAssets.I.birds != null && GameAssets.I.birds.Length > 0)
            {
                nextBird = Time.time + Random.Range(2.5f, 8f);
                Vector2 r = Random.insideUnitCircle.normalized * Random.Range(14f, 38f);
                Vector3 pos = new Vector3(p.x + r.x, p.y + Random.Range(5f, 13f), p.z + r.y);
                Sfx.Play3D(Sfx.Pick(GameAssets.I.birds), pos, Random.Range(0.25f, 0.5f), Random.Range(0.9f, 1.12f), 70f);
            }
        }
    }
}
