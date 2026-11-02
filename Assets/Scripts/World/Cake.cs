using UnityEngine;

namespace NightClass
{
    /// <summary>A slice of cake on the cafeteria counter.</summary>
    public class Cake : Interactable
    {
        public GameObject slice;
        bool eaten;

        public override bool Available { get { return !eaten; } }
        public override string Prompt() { return "Eat the cake"; }

        public override void Interact()
        {
            eaten = true;
            if (slice != null) slice.SetActive(false);
            Sfx.Play2D(GameAssets.I.eat, 0.8f);
            Msg("Stale... but still sweet.", 2.5f);
        }
    }
}
