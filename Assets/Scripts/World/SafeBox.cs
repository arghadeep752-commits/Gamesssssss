using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>The safe in the teachers' lounge. The small key from the boiler room opens it.</summary>
    public class SafeBox : Interactable
    {
        public Transform doorHinge;
        public PickupItem contents;
        bool open;

        public override bool Available { get { return !open; } }
        public override string Prompt() { return Holding(ItemType.SafeKey) ? "Unlock the safe" : "Safe"; }

        public override void Interact()
        {
            if (!Holding(ItemType.SafeKey))
            {
                Sfx.Play3D(GameAssets.I.doorLocked, transform.position, 0.6f, 1.3f);
                Msg("The safe is locked. It takes a small key.", 3f);
                return;
            }
            open = true;
            Inv.Consume();
            Progress.SafeOpen = true;
            StartCoroutine(OpenAnim());
        }

        IEnumerator OpenAnim()
        {
            Sfx.Play3D(GameAssets.I.safeOpen, transform.position, 0.9f);
            Quaternion r0 = doorHinge.localRotation;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 1.1f;
                doorHinge.localRotation = r0 * Quaternion.Euler(0f, -105f * Mathf.SmoothStep(0f, 1f, t), 0f);
                yield return null;
            }
            Collider own = GetComponent<Collider>();
            if (own != null) own.enabled = false;   // let the hand reach the spring inside
            if (contents != null) contents.Unlock();
            Msg("There's a spring inside the safe.", 2.5f);
        }
    }
}
