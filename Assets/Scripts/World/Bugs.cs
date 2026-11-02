using UnityEngine;

namespace NightClass
{
    /// <summary>Cockroaches crawling on a wall or floor patch; they scatter when the player comes close.</summary>
    public class Bugs : MonoBehaviour
    {
        public Transform[] bugs;
        public Vector2 area = new Vector2(1.6f, 1.2f);
        Vector2[] pos, dir;
        float[] speed;
        float hiddenUntil;
        bool scattered;

        void Start()
        {
            int n = bugs.Length;
            pos = new Vector2[n];
            dir = new Vector2[n];
            speed = new float[n];
            for (int i = 0; i < n; i++)
            {
                pos[i] = new Vector2(Random.Range(-area.x, area.x), Random.Range(-area.y, area.y)) * 0.5f;
                dir[i] = Random.insideUnitCircle.normalized;
                speed[i] = Random.Range(0.05f, 0.18f);
            }
        }

        void Update()
        {
            FPController p = FPController.I;
            float d = p != null ? Vector3.Distance(p.transform.position, transform.position) : 99f;
            if (!scattered && d < 2.6f)
            {
                scattered = true;
                hiddenUntil = Time.time + 25f;
                Sfx.Play3D(GameAssets.I.drop, transform.position, 0.15f, 2.4f, 8f);
            }
            if (scattered && Time.time > hiddenUntil && d > 8f)
            {
                scattered = false;
                Start();
            }
            for (int i = 0; i < bugs.Length; i++)
            {
                if (bugs[i] == null) continue;
                if (scattered)
                {
                    pos[i] += dir[i] * 1.6f * Time.deltaTime;
                    if (Mathf.Abs(pos[i].x) > area.x || Mathf.Abs(pos[i].y) > area.y) { bugs[i].gameObject.SetActive(false); continue; }
                }
                else
                {
                    if (!bugs[i].gameObject.activeSelf) bugs[i].gameObject.SetActive(true);
                    if (Random.value < 0.02f) dir[i] = Random.insideUnitCircle.normalized;
                    float move = Mathf.PerlinNoise(Time.time * 0.8f, i * 3.1f) > 0.5f ? speed[i] : 0f;
                    pos[i] += dir[i] * move * Time.deltaTime;
                    if (Mathf.Abs(pos[i].x) > area.x * 0.5f) dir[i].x = -Mathf.Sign(pos[i].x) * Mathf.Abs(dir[i].x);
                    if (Mathf.Abs(pos[i].y) > area.y * 0.5f) dir[i].y = -Mathf.Sign(pos[i].y) * Mathf.Abs(dir[i].y);
                }
                bugs[i].localPosition = new Vector3(pos[i].x, pos[i].y, 0f);
                bugs[i].localRotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(dir[i].y, dir[i].x) * Mathf.Rad2Deg - 90f);
            }
        }
    }
}
