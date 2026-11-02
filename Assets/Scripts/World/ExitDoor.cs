using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>The main entrance: planks off + main key = escape.</summary>
    public class ExitDoor : Interactable
    {
        public Planks planks;
        public Transform leftHinge, rightHinge;
        bool opened;

        public override bool Available { get { return !opened; } }
        public override string Prompt() { return "Open the main door"; }

        public override void Interact()
        {
            if (planks != null && !planks.Broken)
            {
                Sfx.Play3D(GameAssets.I.doorLocked, transform.position, 0.9f);
                Msg("The door is boarded up. You need something to knock the planks off.");
                return;
            }
            if (!Holding(ItemType.MainKey))
            {
                Sfx.Play3D(GameAssets.I.doorLocked, transform.position, 0.9f);
                Msg("It's locked. The main key must be somewhere in the school.");
                return;
            }
            opened = true;
            Inv.Consume();
            Sfx.Play3D(GameAssets.I.keypadOk, transform.position, 0.7f);
            StartCoroutine(OpenAnim());
            NCGame.I.OnEscaped();
        }

        IEnumerator OpenAnim()
        {
            yield return new WaitForSeconds(0.4f);
            Sfx.Play3D(GameAssets.I.doorOpen, transform.position, 1f, 0.8f);
            NavMeshObstacle ob = GetComponent<NavMeshObstacle>();
            if (ob != null) ob.enabled = false;
            Quaternion l0 = leftHinge != null ? leftHinge.localRotation : Quaternion.identity;
            Quaternion r0 = rightHinge != null ? rightHinge.localRotation : Quaternion.identity;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 1.6f;
                float k = Mathf.SmoothStep(0f, 1f, t);
                if (leftHinge != null) leftHinge.localRotation = l0 * Quaternion.Euler(0f, 95f * k, 0f);
                if (rightHinge != null) rightHinge.localRotation = r0 * Quaternion.Euler(0f, -95f * k, 0f);
                yield return null;
            }
        }
    }
}
