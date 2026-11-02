using UnityEngine;

namespace NightClass
{
    public enum ScareKind { LampPop, DoorSlam, Sound }

    /// <summary>One-shot scares: a lamp bursts, a door slams, a sound from nowhere.</summary>
    public class ScareTrigger : MonoBehaviour
    {
        public ScareKind kind;
        public FlickerLight lamp;
        public Door door;
        public AudioClip clip;
        public Transform soundPoint;
        public ParticleSystem sparks;
        bool done;

        void OnTriggerEnter(Collider c)
        {
            if (done || c.GetComponent<FPController>() == null) return;
            if (NCGame.I == null || NCGame.I.State != GameState.Playing) return;
            done = true;
            switch (kind)
            {
                case ScareKind.LampPop:
                    if (lamp != null)
                    {
                        lamp.Kill();
                        Sfx.Play3D(GameAssets.I.lightPop, lamp.transform.position, 1f, 1f, 25f);
                    }
                    if (sparks != null) sparks.Play(true);
                    break;
                case ScareKind.DoorSlam:
                    if (door != null) door.Slam();
                    break;
                case ScareKind.Sound:
                    Vector3 p = soundPoint != null ? soundPoint.position : transform.position;
                    Sfx.Play3D(clip != null ? clip : Sfx.Pick(GameAssets.I.ambientOneShots), p, 1f, 1f, 30f);
                    break;
            }
        }
    }
}
