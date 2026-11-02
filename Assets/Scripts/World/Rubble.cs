using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>Collapsed rubble in the basement tunnel. Dynamite clears it (loudly).</summary>
    public class Rubble : Interactable
    {
        public GameObject rocks;
        public GameObject placedDynamite;
        public ParticleSystem fuseSparks;
        public ParticleSystem dust;
        public Light flash;
        public Collider blocker;
        public NavMeshObstacle obstacle;
        bool armed, cleared;

        public override bool Available { get { return !armed && !cleared; } }
        public override string Prompt() { return Holding(ItemType.Dynamite) ? "Place the dynamite" : "Rubble"; }

        public override void Interact()
        {
            if (!Holding(ItemType.Dynamite))
            {
                Msg("Rubble blocks the tunnel. Something powerful could blast it away.");
                return;
            }
            armed = true;
            Inv.Consume();
            StartCoroutine(Fuse());
        }

        IEnumerator Fuse()
        {
            if (placedDynamite != null) placedDynamite.SetActive(true);
            if (fuseSparks != null) fuseSparks.Play(true);
            AudioSource f = Sfx.Play3D(GameAssets.I.fuse, transform.position, 0.8f, 1f, 18f);
            Msg("RUN! The fuse is lit!", 2.5f);
            yield return new WaitForSeconds(4f);
            if (f != null) f.Stop();
            if (fuseSparks != null) fuseSparks.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            if (placedDynamite != null) placedDynamite.SetActive(false);
            Sfx.Play3D(GameAssets.I.explosion, transform.position, 1f, 1f, 60f);
            TeacherAI.HearNoise(transform.position, 45f);
            if (dust != null) dust.Play(true);
            if (rocks != null) rocks.SetActive(false);
            if (blocker != null) blocker.enabled = false;
            if (obstacle != null) obstacle.enabled = false;
            cleared = true;
            Progress.RubbleCleared = true;
            if (FPController.I != null)
            {
                float d = Vector3.Distance(FPController.I.transform.position, transform.position);
                if (d < 10f) FPController.I.Shake(Mathf.Lerp(0.35f, 0.05f, d / 10f));
            }
            if (flash != null)
            {
                flash.enabled = true;
                float t = 0f;
                while (t < 1f)
                {
                    t += Time.deltaTime / 0.7f;
                    flash.intensity = Mathf.Lerp(12f, 0f, t);
                    yield return null;
                }
                flash.enabled = false;
            }
        }
    }
}
