using UnityEngine;

namespace RealFPS
{
    /// <summary>Slow looping camera flight behind the main menu.</summary>
    public class CinematicCamera : MonoBehaviour
    {
        public Vector3[] points;
        public Vector3[] targets;
        public float segmentTime = 12f;
        public float fieldOfView = 52f;

        Transform cam;
        Camera camera_;
        bool running;
        float t;

        public void Begin(Transform c, bool first)
        {
            cam = c;
            camera_ = c.GetComponent<Camera>();
            if (first) t = 0f;
            running = points != null && points.Length >= 2;
            if (camera_ != null)
            {
                camera_.fieldOfView = fieldOfView;
                camera_.nearClipPlane = 0.5f;   // high above the lake: better depth precision
            }
            LateUpdate();
        }

        public void Stop()
        {
            running = false;
        }

        static Vector3 CatmullRom(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, float u)
        {
            float u2 = u * u, u3 = u2 * u;
            return 0.5f * (2f * p1 + (-p0 + p2) * u + (2f * p0 - 5f * p1 + 4f * p2 - p3) * u2 + (-p0 + 3f * p1 - 3f * p2 + p3) * u3);
        }

        Vector3 Sample(Vector3[] a, float ft)
        {
            int n = a.Length;
            int i = Mathf.FloorToInt(ft);
            float u = ft - i;
            Vector3 p0 = a[((i - 1) % n + n) % n];
            Vector3 p1 = a[i % n];
            Vector3 p2 = a[(i + 1) % n];
            Vector3 p3 = a[(i + 2) % n];
            return CatmullRom(p0, p1, p2, p3, u);
        }

        void LateUpdate()
        {
            if (!running || cam == null) return;
            t += Time.unscaledDeltaTime / Mathf.Max(1f, segmentTime);
            float ft = Mathf.Repeat(t, points.Length);
            Vector3 pos = Sample(points, ft);
            Vector3 target = Sample(targets, ft);
            cam.position = pos;
            Vector3 dir = target - pos;
            if (dir.sqrMagnitude > 0.01f) cam.rotation = Quaternion.LookRotation(dir, Vector3.up);
        }
    }
}
