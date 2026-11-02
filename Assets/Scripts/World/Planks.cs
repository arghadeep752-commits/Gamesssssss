using UnityEngine;

namespace NightClass
{
    /// <summary>Planks nailed across the main entrance. The hammer knocks them off.</summary>
    public class Planks : Interactable
    {
        public Rigidbody[] boards;
        public bool Broken { get; private set; }

        public override bool Available { get { return !Broken; } }
        public override string Prompt() { return Holding(ItemType.Hammer) ? "Break the planks" : "Planks"; }

        public override void Interact()
        {
            if (!Holding(ItemType.Hammer))
            {
                Msg("The door is boarded up. You need something to knock the planks off.");
                return;
            }
            Broken = true;
            Progress.PlanksBroken = true;
            Inv.Consume();
            Sfx.Play3D(GameAssets.I.plankBreak, transform.position, 1f, 1f, 35f);
            TeacherAI.HearNoise(transform.position, 22f);
            foreach (Rigidbody b in boards)
            {
                if (b == null) continue;
                b.gameObject.layer = 10;
                b.isKinematic = false;
                b.AddForce((-transform.forward * 2.2f + Random.insideUnitSphere) * 2.5f, ForceMode.VelocityChange);
                b.AddTorque(Random.insideUnitSphere * 6f, ForceMode.VelocityChange);
            }
            Collider c = GetComponent<Collider>();
            if (c != null) c.enabled = false;
            Msg("The planks are off. Now the lock...", 3f);
        }
    }
}
