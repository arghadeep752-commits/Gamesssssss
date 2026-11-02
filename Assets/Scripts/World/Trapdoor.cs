using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>Floor hatch in the janitor's room. Push it and it drops open onto the basement stairs.</summary>
    public class Trapdoor : Interactable
    {
        public Transform hinge;
        public float openAngle = -115f;
        public NavMeshObstacle blocker;
        bool open;

        public override bool Available { get { return !open; } }
        public override string Prompt() { return "Push the hatch"; }

        public override void Interact()
        {
            open = true;
            Progress.TrapdoorOpen = true;
            StartCoroutine(Fall());
        }

        IEnumerator Fall()
        {
            Collider c = GetComponentInChildren<Collider>();
            Quaternion r0 = hinge.localRotation;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 0.55f;
                float k = t * t;
                hinge.localRotation = r0 * Quaternion.Euler(openAngle * Mathf.Min(1f, k), 0f, 0f);
                yield return null;
            }
            Sfx.Play3D(GameAssets.I.trapdoor, hinge.position, 1f, 1f, 30f);
            TeacherAI.HearNoise(hinge.position, 16f);
            // small bounce
            t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 0.35f;
                float b = Mathf.Sin(t * Mathf.PI) * 6f * (1f - t);
                hinge.localRotation = r0 * Quaternion.Euler(openAngle + b, 0f, 0f);
                yield return null;
            }
            if (c != null) c.enabled = false;
            if (blocker != null) blocker.enabled = false;
            Msg("Stairs lead down into the basement.", 2.5f);
        }
    }
}
