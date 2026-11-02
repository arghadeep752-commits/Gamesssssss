using UnityEngine;

namespace NightClass
{
    /// <summary>An item lying in the world. Locked items (inside the safe / the food elevator) can't be taken yet.</summary>
    public class PickupItem : Interactable
    {
        public ItemType type;
        public bool locked;
        public bool isTemplate;

        public override bool Available { get { return !locked && !isTemplate; } }
        public override string Prompt() { return "Take the " + Items.Name(type); }

        public override void Interact()
        {
            if (Inv != null && Inv.Take(this))
                gameObject.SetActive(false);
        }

        public void Unlock() { locked = false; }
    }
}
