using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>Locker / wardrobe. Standing in front of it shows the HIDE button.</summary>
    public class HidingSpot : MonoBehaviour
    {
        public Transform hidePoint;
        public Transform exitPoint;
        public Transform doorHinge;
        public float doorAngle = 75f;
        Coroutine anim;
        Quaternion closed;
        bool init;

        void Awake()
        {
            if (doorHinge != null) closed = doorHinge.localRotation;
            init = true;
        }

        void OnTriggerEnter(Collider c)
        {
            FPController p = c.GetComponent<FPController>();
            if (p != null) p.SpotInRange = this;
        }

        void OnTriggerExit(Collider c)
        {
            FPController p = c.GetComponent<FPController>();
            if (p != null && p.SpotInRange == this) p.SpotInRange = null;
        }

        public void OnHide() { Swing(0.35f); }
        public void OnUnhide() { Swing(0.35f); }
        public void TeacherOpen()
        {
            if (doorHinge == null || !init) return;
            if (anim != null) StopCoroutine(anim);
            doorHinge.localRotation = closed * Quaternion.Euler(0f, -doorAngle, 0f);
            Sfx.Play3D(GameAssets.I.slam, doorHinge.position, 0.8f, 1.2f);
        }

        void Swing(float dur)
        {
            if (doorHinge == null || !init) return;
            if (anim != null) StopCoroutine(anim);
            anim = StartCoroutine(SwingAnim(dur));
        }

        IEnumerator SwingAnim(float dur)
        {
            Sfx.Play3D(GameAssets.I.doorOpen, doorHinge.position, 0.45f, 1.35f);
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / dur;
                float k = Mathf.Sin(Mathf.Clamp01(t) * Mathf.PI);
                doorHinge.localRotation = closed * Quaternion.Euler(0f, -doorAngle * k, 0f);
                yield return null;
            }
            doorHinge.localRotation = closed;
            Sfx.Play3D(GameAssets.I.doorClose, doorHinge.position, 0.4f, 1.35f);
        }
    }
}
