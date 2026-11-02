using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>Bookshelf in the start classroom that hides a secret room; it only moves after the first escape.</summary>
    public class SecretShelf : Interactable
    {
        public Vector3 slide = new Vector3(1.3f, 0f, 0f);
        bool open;

        public override bool Available { get { return !open; } }
        public override string Prompt() { return "Push the bookshelf"; }

        public override void Interact()
        {
            if (!NCGame.HasEscapedBefore)
            {
                Msg("It won't budge... Something is behind it.", 3f);
                return;
            }
            open = true;
            StartCoroutine(Slide());
        }

        IEnumerator Slide()
        {
            Sfx.Play3D(GameAssets.I.motor, transform.position, 0.5f, 0.6f);
            Vector3 p0 = transform.localPosition;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 2f;
                transform.localPosition = p0 + slide * Mathf.SmoothStep(0f, 1f, t);
                yield return null;
            }
            Msg("A secret room! Only those who escaped know about it.", 3.5f);
        }
    }
}
