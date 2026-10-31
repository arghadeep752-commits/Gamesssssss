using UnityEngine;

namespace RealFPS
{
    /// <summary>Turns a quad to face the camera (glows, flames).</summary>
    public class Billboard : MonoBehaviour
    {
        public bool upright;

        void LateUpdate()
        {
            Camera c = Camera.main;
            if (c == null) return;
            Vector3 d = transform.position - c.transform.position;
            if (upright) d.y = 0f;
            if (d.sqrMagnitude < 1e-6f) return;
            transform.rotation = Quaternion.LookRotation(d, Vector3.up);
        }
    }
}
