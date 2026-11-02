using UnityEngine;

namespace NightClass
{
    /// <summary>Physics props and dropped items: a hard bump makes a sound the teacher comes to check.</summary>
    public class NoiseMaker : MonoBehaviour
    {
        public float loudness = 16f;
        public AudioClip clip;
        float last = -10f;

        void OnCollisionEnter(Collision c)
        {
            float v = c.relativeVelocity.magnitude;
            if (v < 1.6f || Time.time - last < 0.35f) return;
            last = Time.time;
            AudioClip a = clip != null ? clip : GameAssets.I.drop;
            Sfx.Play3D(a, transform.position, Mathf.Clamp01(v / 6f) * 0.9f, Random.Range(0.85f, 1.15f), 25f);
            if (Time.timeSinceLevelLoad > 3f) TeacherAI.HearNoise(transform.position, loudness * Mathf.Clamp01(v / 4f));
        }
    }
}
