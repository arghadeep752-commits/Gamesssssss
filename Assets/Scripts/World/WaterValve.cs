using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>The sprinkler valve in the toilets. Turning it puts out the corridor fire.</summary>
    public class WaterValve : Interactable
    {
        public Transform wheel;
        public ParticleSystem[] sprinklers;
        public FireBarrier fire;
        bool turned;

        public override bool Available { get { return !turned; } }
        public override string Prompt() { return "Turn the sprinkler valve"; }

        public override void Interact()
        {
            turned = true;
            StartCoroutine(Turn());
        }

        IEnumerator Turn()
        {
            Sfx.Play3D(GameAssets.I.doorLocked, wheel.position, 0.5f, 0.6f);
            Quaternion r0 = wheel.localRotation;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 1.6f;
                wheel.localRotation = r0 * Quaternion.Euler(0f, 0f, -540f * Mathf.SmoothStep(0f, 1f, t));
                yield return null;
            }
            Sfx.Play3D(GameAssets.I.water, wheel.position, 0.8f);
            Msg("Water rushes through the pipes...", 2.5f);
            foreach (ParticleSystem s in sprinklers)
            {
                if (s == null) continue;
                s.Play(true);
                Sfx.Loop(s.gameObject, GameAssets.I.water, 0.5f, 16f);
            }
            yield return new WaitForSeconds(1.5f);
            if (fire != null) fire.Extinguish();
            yield return new WaitForSeconds(9f);
            foreach (ParticleSystem s in sprinklers)
            {
                if (s == null) continue;
                s.Stop(true, ParticleSystemStopBehavior.StopEmitting);
                AudioSource a = s.GetComponent<AudioSource>();
                if (a != null) a.Stop();
            }
        }
    }
}
